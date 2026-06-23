import io
import pypdf
import docx
from typing import Dict, Any
import base64

from app.tools.registry import BaseTool


class DocReaderTool(BaseTool):

    @property
    def name(self) -> str:
        return "read_document"

    @property
    def description(self) -> str:
        return (
            "Extract and read text from PDF or DOCX documents."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "file_content_base64": {
                "type": "string",
                "description": "Base64-encoded file content",
            },
            "file_type": {
                "type": "string",
                "description": "File type: 'pdf' or 'docx'",
            },
            "filename": {
                "type": "string",
                "description": "Original filename",
            },
        }

    async def execute(
        self,
        file_content_base64: str,
        file_type: str,
        filename: str = "document",
    ) -> Dict[str, Any]:
        try:
            file_bytes = base64.b64decode(file_content_base64)
            file_obj = io.BytesIO(file_bytes)

            if file_type.lower() == "pdf":
                text = self._extract_pdf(file_obj)
            elif file_type.lower() in ("docx", "doc"):
                text = self._extract_docx(file_obj)
            else:
                return {
                    "success": False,
                    "result": None,
                    "error": f"Unsupported: {file_type}",
                }

            truncated = len(text) > 8000
            text_out = text[:8000] + (
                "\n\n[Truncated]" if truncated else ""
            )

            return {
                "success": True,
                "result": {
                    "filename": filename,
                    "file_type": file_type,
                    "char_count": len(text),
                    "truncated": truncated,
                    "text": text_out,
                },
                "error": None,
            }

        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": f"Failed: {str(e)}",
            }

    def _extract_pdf(self, file_obj: io.BytesIO) -> str:
        reader = pypdf.PdfReader(file_obj)
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages.append(f"--- Page {i+1} ---\n{text.strip()}")
        return "\n\n".join(pages)

    def _extract_docx(self, file_obj: io.BytesIO) -> str:
        doc = docx.Document(file_obj)
        paragraphs = [
            p.text for p in doc.paragraphs if p.text.strip()
        ]
        return "\n\n".join(paragraphs)