from collections.abc import Callable
from typing import Any

from frappe.mcp.tools import Tool, ToolArguments
from pydantic import Field


class NoArguments(ToolArguments):
	pass


class PageArguments(ToolArguments):
	start: int = Field(default=0, ge=0)
	limit: int = Field(default=20, ge=1, le=50)


def read_only_tool(
	name: str, description: str, arguments: type[ToolArguments], handler: Callable[..., Any]
) -> Tool:
	return Tool(
		name=name,
		description=description,
		arguments=arguments,
		handler=handler,
		annotations={"readOnlyHint": True},
	)
