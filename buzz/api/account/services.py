import frappe
from frappe.translate import get_language


def get_request_language() -> str:
	"""Language the current request should be served in.

	Logged-in users resolve from their own User document. Guests all share the
	one `Guest` User, so there is nothing per-visitor to read there — frappe's
	`get_language` picks the `preferred_language` cookie, then the
	`Accept-Language` header, then the System Settings default.
	"""
	if frappe.session.user != "Guest":
		return frappe.db.get_value("User", frappe.session.user, "language") or get_default_language()

	# get_language reads cookies and headers straight off the live request;
	# background jobs and the console have none.
	if not frappe.request:
		return get_default_language()

	return get_language()


def get_default_language() -> str:
	"""Site-wide language from System Settings, falling back to English."""
	return frappe.get_system_settings("language") or "en"
