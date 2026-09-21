from __future__ import annotations

import csv
import io
from typing import Any

import httpx

from config import settings


class AnalyticsError(RuntimeError):
    pass


def configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_secret_key)


def _headers() -> dict[str, str]:
    if not configured():
        raise AnalyticsError("Supabase is not configured")
    # Supabase secret keys are opaque keys, not JWTs.
    # Send them in the `apikey` header; do not put sb_secret_* in
    # Authorization: Bearer, otherwise Supabase can reject it as an invalid JWT.
    return {
        "apikey": settings.supabase_secret_key,
        "Content-Type": "application/json",
    }


def _url(path: str) -> str:
    return f"{settings.supabase_url.rstrip('/')}{path}"


async def insert_event(event: dict[str, Any]) -> None:
    if not configured():
        if settings.analytics_optional:
            return
        raise AnalyticsError("Supabase is not configured")

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            _url("/rest/v1/usage_events"),
            headers={**_headers(), "Prefer": "return=minimal"},
            json=event,
        )
        response.raise_for_status()


async def _rpc(function_name: str) -> Any:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            _url(f"/rest/v1/rpc/{function_name}"),
            headers=_headers(),
            json={},
        )
        response.raise_for_status()
        return response.json()


async def admin_overview() -> dict[str, Any]:
    return await _rpc("admin_overview")


async def admin_course_breakdown() -> list[dict[str, Any]]:
    return await _rpc("admin_course_breakdown")


async def admin_feedback_reasons() -> list[dict[str, Any]]:
    return await _rpc("admin_feedback_reasons")


async def admin_daily_usage() -> list[dict[str, Any]]:
    return await _rpc("admin_daily_usage")


async def export_events_csv(limit: int = 5000) -> str:
    if not configured():
        raise AnalyticsError("Supabase is not configured")

    params = {
        "select": (
            "id,created_at,session_id,event_type,message_id,course,question_type,"
            "language,input_length,output_length,latency_ms,model_version,"
            "feedback,feedback_reason,store_content,question_text,answer_text,user_agent"
        ),
        "order": "created_at.desc",
        "limit": str(max(1, min(limit, 5000))),
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            _url("/rest/v1/usage_events"),
            headers=_headers(),
            params=params,
        )
        response.raise_for_status()
        rows = response.json()

    buffer = io.StringIO()
    if not rows:
        buffer.write("id,created_at,event_type\n")
        return buffer.getvalue()

    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()
