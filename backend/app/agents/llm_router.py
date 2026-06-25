"""
TITAN LLM Router — google-genai (new SDK)
Uses google.genai.Client with ThinkingConfig(thinking_budget=0)
"""
import json
import logging
from typing import AsyncIterator, List, Dict, Optional
from google import genai
from google.genai import types
from app.config import settings

logger = logging.getLogger(__name__)


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


def _build_messages(messages: List[Dict]) -> List[types.Content]:
    """Convert dicts to google.genai Content objects."""
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])]
            )
        )

    # Gemini requires conversation to start with user role
    if not contents or contents[0].role != "user":
        contents.insert(0, types.Content(
            role="user",
            parts=[types.Part(text="Hello")]
        ))
        contents.insert(1, types.Content(
            role="model",
            parts=[types.Part(text="Hello! How can I help you today?")]
        ))

    return contents


async def stream_response(
    system_prompt: str,
    messages: List[Dict],
    task_type: str = "reasoning",
) -> AsyncIterator[str]:
    """Stream response from Gemini 2.5 Flash."""
    try:
        client = _get_client()
        contents = _build_messages(messages)

        config = types.GenerateContentConfig(
            max_output_tokens=8192,
            temperature=0.7 if task_type == "creative" else 0.3,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            system_instruction=system_prompt,
        )

        response = client.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
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
    """Ask Gemini if a tool should be used. Returns tool dict or None."""
    if not messages:
        return None

    last_message = messages[-1]["content"] if messages else ""

    decision_prompt = f"""You are a tool dispatcher. Decide if a tool is needed.

Available tools:
- web_search: For current events, real-time data, latest news, prices, guidelines, anything needing internet
- generate_file: When user wants to CREATE, GENERATE, or DOWNLOAD a file — roster, schedule, tracker, template, Excel, CSV
- send_email: When user explicitly asks to SEND an email
- read_document: When user uploads a document to analyze

User message: {last_message}

Respond ONLY with valid JSON, no markdown, no explanation:
- Web search needed: {{"tool": "web_search", "input": {{"query": "exact search query"}}}}
- File generation needed: {{"tool": "generate_file", "input": {{"file_type": "excel", "filename": "staff_roster", "headers": ["Staff Name", "Role", "Shift", "Date"], "rows": [["Dr. Sharma", "Doctor", "Morning", "01-Jul-2024"], ["Nurse Priya", "Nurse", "Morning", "01-Jul-2024"]], "description": "Monthly staff duty roster"}}}}
- No tool needed: {{"tool": null}}

JSON:"""

    try:
        client = _get_client()

        config = types.GenerateContentConfig(
            max_output_tokens=2048,
            temperature=0.1,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            response_mime_type="application/json",
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[types.Content(
                role="user",
                parts=[types.Part(text=decision_prompt)]
            )],
            config=config,
        )

        text = response.text.strip()
        # Strip markdown if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        parsed = json.loads(text)
        tool = parsed.get("tool")
        if tool and tool in available_tools:
            return parsed
        return None

    except Exception as e:
        logger.warning(f"Tool decision failed: {e}")
        return None
