import frappe
from frappe import _
from frappe.permissions import ALL_USER_ROLE

MCP_METHODS = {"buzz.mcp.endpoint.handle", "frappe.integrations.oauth2.openid_profile"}
METHOD_PREFIXES = ("/api/method", "/api/v1/method", "/api/v2/method")


def confine_mcp_tokens() -> None:
	"""A token issued to a dynamically registered client, as MCP clients are, works only for MCP.

	Without this, the token is a full API credential for whoever signs in.
	"""
	client = frappe.session.data.get("oauth_client")
	if not client or not frappe.get_cached_value("OAuth Client", client, "is_dynamic_client"):
		return
	if requested_method() not in MCP_METHODS:
		frappe.throw(_("This token can only be used with the Buzz MCP server."), frappe.PermissionError)


def requested_method() -> str | None:
	# `cmd` runs before path routing in frappe.app, so it decides what actually runs.
	if frappe.form_dict.cmd:
		return frappe.form_dict.cmd
	prefix, _separator, method = frappe.request.path.removesuffix("/").rpartition("/")
	return method if prefix in METHOD_PREFIXES else None


def open_to_every_user(doc, method=None) -> None:
	"""Attendees are Website Users, whom Frappe's default role for a new OAuth Client shuts out.

	Safe because `confine_mcp_tokens` limits these clients' tokens to MCP.
	"""
	if doc.is_dynamic_client and not doc.allowed_roles:
		doc.append("allowed_roles", {"role": ALL_USER_ROLE})
