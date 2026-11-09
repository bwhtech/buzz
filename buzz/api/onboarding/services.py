import re

import frappe
from frappe import _

from buzz.api.events.schemas import RouteAvailability
from buzz.api.onboarding.exceptions import InvalidUsername

USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,29}$")
STATUS_FIELD = "buzz_onboarding_status"


def onboarding_enabled() -> bool:
	return bool(frappe.db.get_single_value("Buzz Settings", "enable_onboarding"))


def mark_pending_on_signup(doc, event=None):
	"""New users onboard only while the setting is on; earlier users stay blank, which counts as done."""
	if onboarding_enabled():
		frappe.db.set_value("User", doc.name, STATUS_FIELD, "Pending")


def needs_onboarding(user: str) -> bool:
	if not onboarding_enabled():
		return False
	return frappe.db.get_value("User", user, STATUS_FIELD) in ("Pending", "Deferred")


def is_valid_username(username: str) -> bool:
	return bool(USERNAME_PATTERN.match(username))


def username_taken(username: str, user: str) -> bool:
	return bool(frappe.db.exists("User", {"username": username, "name": ("!=", user)}))


def username_availability(username: str, user: str) -> RouteAvailability:
	if not is_valid_username(username):
		return RouteAvailability(available=False, message=str(InvalidUsername.message))
	if username_taken(username, user):
		return RouteAvailability(available=False, message=_("That username is taken"))
	return RouteAvailability(available=True, message=_("Available"))
