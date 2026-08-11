import frappe
from frappe.translate import get_language


def get_request_language() -> str:
	"""Language the current request should be served in.

	A logged-in user's own User document, else `get_language`'s order:
	`preferred_language` cookie, `Accept-Language` header, System Settings.
	"""
	if frappe.session.user != "Guest":
		return frappe.db.get_value("User", frappe.session.user, "language") or get_default_language()

	# get_language reads cookies and headers off the live request; background
	# jobs and the console have none.
	if not frappe.request:
		return get_default_language()

	return get_language()


def get_default_language() -> str:
	return frappe.get_system_settings("language") or "en"
