from functools import lru_cache

import frappe
import pytz
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


@lru_cache(maxsize=1)
def accepted_timezones() -> frozenset[str]:
	"""Zone names a user may store.

	`all_timezones` rather than `common_timezones`: the dashboard builds its picker
	from `Intl.supportedValuesOf`, whose list is close but not identical, and it
	sends back the runtime's own spelling. The wider set covers both without
	rejecting a zone the browser considers current.
	"""
	return frozenset(pytz.all_timezones)
