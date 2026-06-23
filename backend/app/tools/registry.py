from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


# ─── Base Tool ────────────────────────────────────────────────────────────────

class BaseTool(ABC):
    """Every tool must implement name, description, and execute()."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique snake_case identifier. Agent uses this to call the tool."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """One-line description. Agent uses this to decide WHEN to call the tool."""
        ...

    @property
    def parameters(self) -> Dict[str, Any]:
        """
        JSON Schema for the tool's input parameters.
        Override in each tool.
        """
        return {}

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Run the tool. Always returns a dict with at minimum:
          { "success": bool, "result": Any, "error": str|None }
        """
        ...

    def to_claude_tool_spec(self) -> Dict[str, Any]:
        """Format this tool for the Claude API tool_use block."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": list(self.parameters.keys()),
            },
        }


# ─── Tool Registry ────────────────────────────────────────────────────────────

class ToolRegistry:
    """
    Central registry of all available tools.
    Agents get tools by name; the registry handles instantiation.
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool
        logger.info(f"Tool registered: {tool.name}")

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def all_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def claude_tool_specs(self) -> List[Dict[str, Any]]:
        """Returns all tools formatted for the Claude API."""
        return [t.to_claude_tool_spec() for t in self._tools.values()]

    async def execute(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name. Returns error dict if tool not found."""
        tool = self.get(tool_name)
        if not tool:
            return {"success": False, "result": None, "error": f"Tool '{tool_name}' not found"}
        try:
            result = await tool.execute(**kwargs)
            logger.info(f"Tool executed: {tool_name} → success={result.get('success')}")
            return result
        except Exception as e:
            logger.error(f"Tool error [{tool_name}]: {e}")
            return {"success": False, "result": None, "error": str(e)}


# ─── Singleton ────────────────────────────────────────────────────────────────
tool_registry = ToolRegistry()
