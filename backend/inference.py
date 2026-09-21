from __future__ import annotations

from typing import Any

import httpx

from calculator_bridge import fix_arithmetic
from config import settings


SYSTEM_PROMPT = """You are BAH (Business Academic Helper), a business-school academic assistant.

Purpose:
- Help business-administration students understand questions and create strong first drafts.
- Prioritise clear academic structure, correct calculations, business interpretation, and evidence-aware reasoning.

Answering rules:
1. Answer the user's actual question directly.
2. Calculations: show formula -> substitution -> result -> business interpretation.
3. Theory: define the concept, explain the key points, then give a relevant example when useful.
4. Case studies: identify the issue, analyse evidence, connect evidence to business implications, and make practical recommendations when asked.
5. Report/essay requests: provide logical headings and paragraph structure. Do not pretend to have verified sources that were not provided.
6. Never invent citations, page numbers, statistics, company facts, laws, standards, or references. When current or source-specific facts are required but no source was supplied, say what should be verified.
7. Use the requested language. Preserve common business/accounting terms in English where that improves clarity.
8. Do not claim that an answer is guaranteed to receive a particular grade.
9. Help the student learn and improve the work. Do not fabricate personal experiences or submit-ready misconduct instructions.
"""


def build_messages(req: Any) -> list[dict[str, str]]:
    detail_map = {
        "concise": "Keep the response concise and focus on the essential steps.",
        "standard": "Use a clear, moderately detailed academic answer.",
        "detailed": "Give a detailed answer with headings, reasoning, formulas where relevant, and a concise interpretation.",
    }

    context = (
        f"Course: {req.course}\n"
        f"Question type: {req.question_type}\n"
        f"Language: {req.language}\n"
        f"Detail level: {req.detail}\n"
        f"Response instruction: {detail_map[req.detail]}"
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + context}
    ]

    for item in req.history[-settings.max_history_messages :]:
        messages.append({"role": item.role, "content": item.content})

    messages.append({"role": "user", "content": req.message})
    return messages


async def generate_answer(req: Any) -> tuple[str, dict[str, Any], list]:
    if settings.inference_mode.lower() == "mock":
        answer = (
            "### BAH Web v2 Test\n\n"
            "The web interface, FastAPI backend, and analytics pipeline are connected.\n\n"
            f"**Course:** {req.course}\n\n"
            f"**Question type:** {req.question_type}\n\n"
            f"**Language:** {req.language}\n\n"
            "Set `INFERENCE_MODE=remote` only after the vLLM service is working."
        )
        return answer, {"model": "mock", "prompt_tokens": 0, "completion_tokens": 0}, []

    url = f"{settings.vllm_base_url.rstrip('/')}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if settings.vllm_api_key:
        headers["Authorization"] = f"Bearer {settings.vllm_api_key}"

    payload = {
        "model": settings.vllm_model,
        "messages": build_messages(req),
        "temperature": settings.temperature,
        "max_tokens": settings.max_new_tokens,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("vLLM returned no choices")

    answer = choices[0].get("message", {}).get("content", "").strip()
    if not answer:
        raise RuntimeError("vLLM returned an empty answer")

    fixed, corrections = fix_arithmetic(answer)
    usage = data.get("usage") or {}

    meta = {
        "model": data.get("model", settings.vllm_model),
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "calculator_corrections": len(corrections),
    }
    return fixed, meta, corrections
