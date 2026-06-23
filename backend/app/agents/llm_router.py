import google.generativeai as genai
from typing import AsyncIterator, List, Dict
import logging

from app.config import settings

logger = logging.getLogger(__name__)

_gemini_configured = False


def configure_gemini():
    global _gemini_configured
    if not _gemini_configured:
        genai.configure(api_key=settings.gemini_api_key)
        _gemini_configured = True


def estimate_tokens(messages: List[Dict]) -> int:
    total_chars = sum(len(m.get("content", "")) for m in messages)
    return total_chars // 4


async def stream_gemini(system_prompt: str, messages: List[Dict]) -> AsyncIterator[str]:
    configure_gemini()

    # Build history — all except last message
    gemini_history = []
    for msg in messages[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({
            "role": role,
            "parts": [{"text": msg["content"]}],
        })

    last_message = messages[-1]["content"] if messages else "Hello"

    # gemini-2.5-flash — available on your account
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
    )

    # Build full prompt with system instruction manually
    full_prompt = f"{system_prompt}\n\nUser: {last_message}"

    response = model.generate_content(full_prompt)
    yield response.text


async def stream_response(
    system_prompt: str,
    messages: List[Dict],
    task_type: str = "general",
    force_model: str = None,
) -> AsyncIterator[str]:
    token_estimate = estimate_tokens(messages)
    logger.info(f"LLM → gemini-2.5-flash | task={task_type} | ~{token_estimate} tokens")

    async for chunk in stream_gemini(system_prompt, messages):
        yield chunk