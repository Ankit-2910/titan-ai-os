"""
TITAN LLM Router — Gemini 2.5 Flash
Handles streaming, tool decisions, and response generation.
"""
import json
import logging
from typing import AsyncIterator, List, Dict, Optional
import google.generativeai as genai
from app.config import settings

logger = logging.getLogger(__name__)

# Configure Gemini
if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)


def _build_gemini_model(task_type: str = "reasoning"):
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config=genai.GenerationConfig(
            max_output_tokens=8192,
            temperature=0.7 if task_type == "creative" else 0.3,
            thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
        ),
    )


def _format_messages(system_prompt: str, messages: List[Dict]) -> List[Dict]:
    """Convert messages to Gemini format."""
    formatted = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        formatted.append({"role": role, "parts": [{"text": msg["content"]}]})

    # Gemini needs conversation to start with user
    if not formatted or formatted[0]["role"] != "user":
        formatted.insert(0, {"role": "user", "parts": [{"text": "Hello"}]})
        formatted.insert(1, {"role": "model", "parts": [{"text": "Hello! How can I help?"}]})

    return formatted


async def stream_response(
    system_prompt: str,
    messages: List[Dict],
    task_type: str = "reasoning",
) -> AsyncIterator[str]:
    """Stream response from Gemini."""
    try:
        model = _build_gemini_model(task_type)
        formatted = _format_messages(system_prompt, messages)

        response = model.generate_content(
            formatted,
            stream=True,
            generation_config=genai.GenerationConfig(
                max_output_tokens=8192,
                temperature=0.3,
                thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
            ),
            system_instruction=system_prompt,
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text

    except Exception as e:
        logger.error(f"Gemini stream error: {e}")
        yield f"⚠️ Response error: {str(e)}"


async def get_tool_decision(
    system_prompt: str,
    messages: List[Dict],
    available_tools: List[str],
) -> Optional[Dict]:
    """
    Ask Gemini whether a tool should be used.
    Returns {"tool": "web_search", "input": {"query": "..."}} or None.
    """
    if not messages:
        return None

    last_message = messages[-1]["content"] if messages else ""

    decision_prompt = f"""You are a tool dispatcher. Given the user's message, decide if a tool should be used.

Available tools:
- web_search: Use when user asks about current events, real-time data, recent news, current prices, latest guidelines, or anything that requires internet search
- generate_file: Use when user asks to CREATE, GENERATE, or DOWNLOAD a file — roster, schedule, tracker, template, Excel, CSV, report format
- send_email: Use when user explicitly asks to SEND an email
- read_document: Use when user uploads a document

User's last message: {last_message}

Respond ONLY with valid JSON — no explanation, no markdown:
- If tool needed: {{"tool": "web_search", "input": {{"query": "search query here"}}}}
- If generate_file: {{"tool": "generate_file", "input": {{"file_type": "excel", "filename": "roster", "headers": ["Name", "Shift", "Date"], "rows": [["Dr. Sharma", "Morning", "01-Jul"]], "description": "Staff roster template"}}}}
- If no tool: {{"tool": null}}

JSON response:"""

    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=genai.GenerationConfig(
                max_output_tokens=1024,
                temperature=0.1,
                thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json",
            ),
        )
        response = model.generate_content(decision_prompt)
        text = response.text.strip()
        parsed = json.loads(text)
        if parsed.get("tool") in available_tools:
            return parsed
        return None
    except Exception as e:
        logger.warning(f"Tool decision failed: {e}")
        return None
