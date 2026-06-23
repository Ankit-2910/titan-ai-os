import httpx
from typing import Dict, Any, Optional

from app.tools.registry import BaseTool
from app.config import settings


class EmailSendTool(BaseTool):
    """
    Sends emails via the Resend API.
    Uses the RESEND_API_KEY and RESEND_FROM_EMAIL from .env.
    Already configured in the Shivanchal stack (intel@shivanchal.in).
    """

    @property
    def name(self) -> str:
        return "send_email"

    @property
    def description(self) -> str:
        return (
            "Send an email to one or more recipients. Use when the user asks to "
            "send, draft and send, or email someone. Always confirm recipient and "
            "subject before sending."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "to": {
                "type": "string",
                "description": "Recipient email address (single address)",
            },
            "subject": {
                "type": "string",
                "description": "Email subject line",
            },
            "body": {
                "type": "string",
                "description": "Plain text or HTML email body",
            },
            "reply_to": {
                "type": "string",
                "description": "Optional reply-to email address",
            },
        }

    async def execute(
        self,
        to: str,
        subject: str,
        body: str,
        reply_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not settings.resend_api_key:
            return {
                "success": False,
                "result": None,
                "error": "RESEND_API_KEY not configured",
            }

        payload: Dict[str, Any] = {
            "from": settings.resend_from_email,
            "to": [to],
            "subject": subject,
            "html": body if body.strip().startswith("<") else f"<p>{body.replace(chr(10), '<br>')}</p>",
            "text": body,
        }
        if reply_to:
            payload["reply_to"] = reply_to

        headers = {
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                json=payload,
                headers=headers,
            )

        if response.status_code in (200, 201):
            data = response.json()
            return {
                "success": True,
                "result": {
                    "email_id": data.get("id"),
                    "to": to,
                    "subject": subject,
                    "message": "Email sent successfully",
                },
                "error": None,
            }
        else:
            return {
                "success": False,
                "result": None,
                "error": f"Resend API error {response.status_code}: {response.text}",
            }
