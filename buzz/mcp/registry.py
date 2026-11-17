import frappe
from frappe.mcp.protocol import METHOD_NOT_FOUND, McpError
from frappe.mcp.tools import Tool
from frappe.permissions import SYSTEM_USER_ROLE

from buzz.mcp.tools.attendee import ATTENDEE_TOOLS
from buzz.permissions import my_team_names


def tools_for_user() -> tuple[Tool, ...]:
	"""Everyone gets the attendee tools; people who run events also get the organizer tools."""
	from buzz.mcp.tools.organizer import ORGANIZER_TOOLS

	if runs_events(frappe.session.user):
		return ATTENDEE_TOOLS + ORGANIZER_TOOLS
	return ATTENDEE_TOOLS


def runs_events(user: str) -> bool:
	# Organizers are mostly Website Users, so the role alone does not find them.
	return (
		SYSTEM_USER_ROLE in frappe.get_roles(user)
		or bool(my_team_names(user))
		or bool(frappe.db.exists("Buzz Event Collaborator", {"user": user, "status": "Accepted"}))
	)


def find_tool(name: object) -> Tool:
	tool = next((tool for tool in tools_for_user() if tool.name == name), None)
	if tool is None:
		raise McpError(METHOD_NOT_FOUND, "Unknown tool: {0}".format(name), status=404)
	return tool
