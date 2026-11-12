import re

import frappe
from frappe import _

from buzz.api.events.schemas import RouteAvailability
from buzz.api.onboarding.exceptions import InvalidUsername
from buzz.api.onboarding.invited import invited_team
from buzz.api.onboarding.schemas import OnboardingState
from buzz.api.onboarding.setup import community_draft, event_draft
from buzz.events.doctype.buzz_team.buzz_team import personal_teams_enabled

USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,29}$")
STATUS_FIELD = "buzz_onboarding_status"


def onboarding_enabled() -> bool:
	return bool(frappe.db.get_single_value("Buzz Settings", "enable_onboarding"))


def mark_pending_on_signup(doc, event=None):
	"""New users onboard only while the setting is on; earlier users stay blank, which counts as done.

	Signup during ticket booking sends `skip_onboarding`, which frappe's sign_up ignores as an
	argument but leaves in form_dict. That user onboards on their next visit to the dashboard.
	"""
	# Staff and integration accounts made in Desk are System Users and skip onboarding.
	if not onboarding_enabled() or doc.user_type != "Website User":
		return
	status = "Deferred" if frappe.form_dict.get("skip_onboarding") else "Pending"
	doc.db_set(STATUS_FIELD, status)


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


def onboarding_state(user: str) -> OnboardingState:
	return OnboardingState(
		personal_teams_enabled=personal_teams_enabled(),
		communities_enabled=bool(frappe.db.get_single_value("Buzz Settings", "enable_communities")),
		invited_team=invited_team(user),
		community=community_draft(user),
		draft_event=event_draft(user),
	)
