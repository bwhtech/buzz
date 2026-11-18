import frappe
from frappe import _
from frappe.permissions import ALL_USER_ROLE

MCP_METHODS = {"buzz.mcp.endpoint.handle", "frappe.integrations.oauth2.openid_profile"}
METHOD_PREFIXES = ("/api/method", "/api/v1/method", "/api/v2/method")


def confine_mcp_tokens() -> None:
	"""A token issued to a dynamically registered client, as MCP clients are, works only for MCP.

	Without this, the token is a full API credential for whoever signs in.
	"""
	client = bearer_client()
	if not client or not is_mcp_client(frappe.get_cached_doc("OAuth Client", client)):
		return
	if requested_method() not in MCP_METHODS:
		frappe.throw(_("This token can only be used with the Buzz MCP server."), frappe.PermissionError)


def bearer_client() -> str | None:
	"""The OAuth Client whose bearer token signed this request in, if one did."""
	if client := frappe.session.data.get("oauth_client"):
		return client
	scheme, _separator, token = frappe.get_request_header("Authorization", "").partition(" ")
	if scheme.lower() != "bearer" or frappe.session.user == "Guest":
		return None
	# Frappe 16 keeps no client on the session, and names the token row by the raw token.
	return frappe.db.get_value("OAuth Bearer Token", token, "client")


def is_mcp_client(client) -> bool:
	# Frappe 16 has no is_dynamic_client flag; registration is the only way a Guest creates a client.
	return bool(client.get("is_dynamic_client")) or client.owner == "Guest"


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
	if is_mcp_client(doc) and not doc.allowed_roles:
		doc.append("allowed_roles", {"role": ALL_USER_ROLE})
