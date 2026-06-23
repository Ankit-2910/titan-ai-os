import httpx
from typing import Dict, Any, List

from app.tools.registry import BaseTool
from app.config import settings


class WebSearchTool(BaseTool):
    """
    Searches the web using the Tavily API.
    Returns top 5 results with title, URL, and snippet.
    Sign up free at https://tavily.com — 1000 searches/month on free tier.
    """

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the web for current information. Use when the user asks about "
            "recent events, real-time data, news, or anything that may have changed recently."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "query": {
                "type": "string",
                "description": "The search query to look up on the web",
            },
            "max_results": {
                "type": "integer",
                "description": "Number of results to return (1-10). Default: 5",
            },
        }

    async def execute(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        if not settings.tavily_api_key:
            return {
                "success": False,
                "result": None,
                "error": "TAVILY_API_KEY not configured",
            }

        payload = {
            "api_key": settings.tavily_api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": min(max_results, 10),
            "include_answer": True,        # Tavily returns a pre-synthesized answer
            "include_raw_content": False,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post("https://api.tavily.com/search", json=payload)
            response.raise_for_status()
            data = response.json()

        results: List[Dict] = []
        for r in data.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", "")[:500],   # cap snippet length
            })

        return {
            "success": True,
            "result": {
                "answer": data.get("answer", ""),    # Tavily's synthesized answer
                "results": results,
                "query": query,
            },
            "error": None,
        }
