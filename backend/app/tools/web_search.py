import httpx
from typing import Dict, Any, Optional
from app.tools.registry import BaseTool
from app.config import settings


class WebSearchTool(BaseTool):

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the internet for current, real-time information on any topic."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "query": {
                "type": "string",
                "description": "The search query to look up on the internet",
            }
        }

    async def execute(self, query: str) -> Dict[str, Any]:
        if not settings.tavily_api_key:
            return {
                "success": False,
                "result": None,
                "error": "Tavily API key not configured",
            }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.tavily_api_key,
                        "query": query,
                        "search_depth": "basic",
                        "max_results": 5,
                        "include_answer": True,
                    },
                )
                response.raise_for_status()
                data = response.json()

            # Build clean result
            results = []
            for r in data.get("results", [])[:5]:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:400],
                })

            return {
                "success": True,
                "result": {
                    "answer": data.get("answer", ""),
                    "results": results,
                    "query": query,
                },
                "error": None,
            }

        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": f"Search failed: {str(e)}",
            }
