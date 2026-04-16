"""Central tool registry — decorator-based registration pattern."""

from __future__ import annotations

from typing import Any, Callable

from utils.logger import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """Register and retrieve callable tools by name.

    Usage::

        registry = ToolRegistry()

        @registry.tool
        def my_tool(arg: str) -> str:
            return f"result: {arg}"

        fn = registry.get("my_tool")
        fn("hello")
    """

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {}

    # --- Decorator ---

    def tool(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        """Register *fn* under its ``__name__``."""
        name = fn.__name__
        self._tools[name] = fn
        logger.debug(f"Registered tool: {name}")
        return fn

    # --- Lookup ---

    def get(self, name: str) -> Callable[..., Any]:
        """Return the tool callable or raise KeyError."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found in registry")
        return self._tools[name]

    def list_tools(self) -> list[str]:
        """Return sorted list of registered tool names."""
        return sorted(self._tools.keys())


# Singleton registry used across the platform
registry = ToolRegistry()
