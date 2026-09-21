from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from analytics import (
    AnalyticsError,
    admin_course_breakdown,
    admin_daily_usage,
    admin_feedback_reasons,
    admin_overview,
    configured as analytics_configured,
    export_events_csv,
    insert_event,
)
from config import settings
from inference import generate_answer
from schemas import ChatRequest, FeedbackRequest


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

allowed_origins = [x.strip() for x in settings.frontend_origin.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Admin-Key"],
)


# This is an in-memory limiter. It is appropriate for a single backend instance.
# If you later run multiple replicas, move rate limiting to Redis/Upstash.
rate_buckets: dict[str, deque[float]] = defaultdict(deque)


def client_key(request: Request, session_id: str) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return f"{ip}:{session_id}"


def enforce_rate_limit(request: Request, session_id: str) -> None:
    key = client_key(request, session_id)
    now = time.time()
    bucket = rate_buckets[key]
    while bucket and now - bucket[0] > settings.rate_limit_window_seconds:
        bucket.popleft()
    if len(bucket) >= settings.rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="Too many requests. Please try again shortly.")
    bucket.append(now)


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    if not settings.admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/")
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "ok",
    }


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "environment": settings.environment,
        "inference_mode": settings.inference_mode,
        "model_version": settings.model_version,
        "analytics_configured": analytics_configured(),
    }


@app.post("/api/chat")
async def chat(payload: ChatRequest, request: Request) -> dict:
    enforce_rate_limit(request, payload.session_id)
    started = time.perf_counter()
    message_id = str(uuid.uuid4())

    try:
        answer, meta, corrections = await generate_answer(payload)
    except Exception as exc:
        # Do not send provider internals, API keys, or stack traces to users.
        raise HTTPException(status_code=502, detail="The AI service is temporarily unavailable.") from exc

    latency_ms = int((time.perf_counter() - started) * 1000)

    event = {
        "session_id": payload.session_id,
        "event_type": "chat",
        "message_id": message_id,
        "course": payload.course,
        "question_type": payload.question_type,
        "language": payload.language,
        "input_length": len(payload.message),
        "output_length": len(answer),
        "latency_ms": latency_ms,
        "model_version": settings.model_version,
        "feedback": None,
        "feedback_reason": None,
        "store_content": payload.store_content,
        "question_text": payload.message if payload.store_content else None,
        "answer_text": answer if payload.store_content else None,
        "user_agent": request.headers.get("user-agent", "")[:500],
    }

    try:
        await insert_event(event)
    except Exception:
        # Logging/analytics failure must not make a successful AI answer unusable.
        pass

    return {
        "message_id": message_id,
        "answer": answer,
        "model_version": settings.model_version,
        "latency_ms": latency_ms,
        "meta": {
            **meta,
            "calculator_corrections": len(corrections),
        },
    }


@app.post("/api/feedback")
async def feedback(payload: FeedbackRequest) -> dict:
    event = {
        "session_id": payload.session_id,
        "event_type": "feedback",
        "message_id": payload.message_id,
        "course": payload.course,
        "question_type": payload.question_type,
        "feedback": payload.rating,
        "feedback_reason": payload.reason,
        "store_content": payload.store_content,
        "question_text": payload.question_text if payload.store_content else None,
        "answer_text": payload.answer_text if payload.store_content else None,
        "model_version": settings.model_version,
    }

    try:
        await insert_event(event)
    except AnalyticsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Failed to save feedback.") from exc

    return {"status": "saved"}


@app.get("/api/admin/overview", dependencies=[Depends(require_admin)])
async def get_admin_overview() -> dict:
    try:
        return {
            "overview": await admin_overview(),
            "course_breakdown": await admin_course_breakdown(),
            "feedback_reasons": await admin_feedback_reasons(),
            "daily_usage": await admin_daily_usage(),
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Analytics service unavailable.") from exc


@app.get("/api/admin/export", dependencies=[Depends(require_admin)])
async def admin_export() -> PlainTextResponse:
    try:
        csv_text = await export_events_csv()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Export failed.") from exc

    return PlainTextResponse(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bah_usage_events.csv"},
    )
