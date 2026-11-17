import frappe
from frappe.mcp.transport import RequestContext
from frappe.rate_limiter import rate_limit
from werkzeug.exceptions import NotFound
from werkzeug.wrappers import Response

from buzz.mcp.server import McpServer

NO_LIMIT = 10**9


def requests_per_minute() -> int:
	return frappe.db.get_single_value("Buzz Settings", "mcp_requests_per_minute") or NO_LIMIT


# Guests must reach the endpoint to get the 401 that starts an MCP client's OAuth flow.
# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["GET", "POST", "DELETE"])
@rate_limit(endpoint="buzz.mcp.endpoint.handle", limit=requests_per_minute, seconds=60, user_based=True)
def handle() -> Response:
	if not frappe.db.get_single_value("Buzz Settings", "enable_mcp"):
		raise NotFound
	frappe.local.mcp_request = RequestContext()
	return McpServer(frappe.request).respond()
