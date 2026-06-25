"""
TITAN LLM Router — Multi-Model Fallback System
Primary: gemini-2.5-flash
Fallback 1: gemini-1.5-flash  
Fallback 2: gemini-1.5-pro
No thinking mode — works on all environments guaranteed.
"""
import json
import logging
from typing import AsyncIterator, List, Dict, Optional
from google import genai
from google.genai import types
from app.config import settings

logger = logging.getLogger(__name__)

# Model cascade — if primary fails, next one takes over automatically
MODEL_CASCADE = [
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


def _build_contents(messages: List[Dict]) -> List[types.Content]:
    """Convert message dicts to Gemini Content objects."""
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        text = msg.get("content", "")
        if text:
            contents.append(
                types.Content(role=role, parts=[types.Part(text=text)])
            )

    # Gemini requires conversation to start with user
    if not contents or contents[0].role != "user":
        contents.insert(0, types.Content(
            role="user", parts=[types.Part(text="Hello")]
        ))
        contents.insert(1, types.Content(
            role="model", parts=[types.Part(text="Hello! How can I help?")]
        ))

    # Ensure last message is from user
    if contents and contents[-1].role != "user":
        contents = contents[:-1]
        if not contents:
            contents = [types.Content(role="user", parts=[types.Part(text="Continue")])]

    return contents


async def stream_response(
    system_prompt: str,
    messages: List[Dict],
    task_type: str = "reasoning",
) -> AsyncIterator[str]:
    """
    Stream response with automatic model fallback.
    Tries each model in MODEL_CASCADE until one succeeds.
    """
    client = _get_client()
    contents = _build_contents(messages)

    config = types.GenerateContentConfig(
        max_output_tokens=8192,
        temperature=0.7 if task_type == "creative" else 0.3,
        system_instruction=system_prompt,
    )

    last_error = None
    for model_name in MODEL_CASCADE:
        try:
            response = client.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config=config,
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
            return  # Success — stop trying other models

        except Exception as e:
            last_error = e
            logger.warning(f"Model {model_name} failed: {e} — trying next model")
            continue

    # All models failed
    logger.error(f"All models failed. Last error: {last_error}")
    yield f"⚠️ AI service temporarily unavailable. Please try again in a moment."


async def get_tool_decision(
    system_prompt: str,
    messages: List[Dict],
    available_tools: List[str],
) -> Optional[Dict]:
    """
    Decide which tool to use (if any).
    Uses fastest model with JSON response mode.
    Falls back gracefully — returns None on any error.
    """
    if not messages:
        return None

    last_message = messages[-1].get("content", "") if messages else ""
    if not last_message:
        return None

    decision_prompt = f"""You are a tool dispatcher. Decide if a tool is needed for the user's request.

Available tools:
- web_search: Use when user asks about current events, real-time data, latest news, prices, guidelines, or anything needing internet search
- generate_file: Use when user wants to CREATE, GENERATE, or DOWNLOAD a file — roster, schedule, tracker, template, Excel, CSV, report
- send_email: Use ONLY when user explicitly asks to SEND an email to someone
- read_document: Use when user uploads a document

User's request: {last_message}

Rules:
- If user says "make Excel", "create roster", "generate file", "download", "template" → use generate_file
- If user asks about current news, prices, rates, latest guidelines → use web_search
- If simple question answerable from knowledge → tool: null
- For generate_file, create realistic sample data with 5-10 rows matching the request

Respond ONLY with JSON (no markdown, no explanation):
Examples:
{{"tool": "web_search", "input": {{"query": "Ayushman Bharat hospital empanelment rates 2024"}}}}
{{"tool": "generate_file", "input": {{"file_type": "excel", "filename": "staff_duty_roster", "headers": ["Staff Name", "Designation", "Department", "Shift", "Date", "In Time", "Out Time", "Status"], "rows": [["Dr. Sharma", "Senior Doctor", "OPD", "Morning", "01-Jul-2024", "08:00", "14:00", "Present"], ["Nurse Priya", "Staff Nurse", "ICU", "Morning", "01-Jul-2024", "08:00", "14:00", "Present"], ["Dr. Khan", "Junior Doctor", "Emergency", "Evening", "01-Jul-2024", "14:00", "20:00", "Present"], ["Nurse Raj", "Staff Nurse", "Ward", "Evening", "01-Jul-2024", "14:00", "20:00", "Present"], ["Dr. Gupta", "Senior Doctor", "Surgery", "Night", "01-Jul-2024", "20:00", "08:00", "Present"]], "description": "20-staff dual shift duty roster for NABH hospital"}}}}
{{"tool": null}}

JSON response:"""

    client = _get_client()

    # Try models for tool decision — use fastest first
    for model_name in ["gemini-2.5-flash", "gemini-1.5-flash"]:
        try:
            config = types.GenerateContentConfig(
                max_output_tokens=2048,
                temperature=0.1,
                response_mime_type="application/json",
            )

            response = client.models.generate_content(
                model=model_name,
                contents=[types.Content(
                    role="user",
                    parts=[types.Part(text=decision_prompt)]
                )],
                config=config,
            )

            text = response.text.strip()
            # Strip markdown if model added it anyway
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            parsed = json.loads(text)
            tool = parsed.get("tool")
            if tool and tool in available_tools:
                logger.info(f"Tool decision: {tool} via {model_name}")
                return parsed
            return None

        except json.JSONDecodeError:
            logger.warning(f"JSON parse failed for tool decision on {model_name}")
            return None
        except Exception as e:
            logger.warning(f"Tool decision failed on {model_name}: {e}")
            continue

    return None  # No tool — proceed with normal response
