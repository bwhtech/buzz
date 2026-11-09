import frappe

from buzz.api.events.schemas import RouteAvailability
from buzz.api.onboarding import services, setup
from buzz.api.onboarding.exceptions import InvalidUsername, UsernameTaken
from buzz.api.onboarding.schemas import FirstEvent, OnboardingState


@frappe.whitelist()
def check_username(username: str) -> RouteAvailability:
	return services.username_availability(username, frappe.session.user)


# Frappe blanks a taken username on save instead of failing, so it is checked here first.
@frappe.whitelist(methods=["POST"])
def save_profile(
	first_name: str, username: str, last_name: str | None = None, user_image: str | None = None
) -> None:
	if not first_name.strip():
		frappe.throw(frappe._("First name is required"))
	if not services.is_valid_username(username):
		InvalidUsername.throw()
	if services.username_taken(username, frappe.session.user):
		UsernameTaken.throw(username=username)
	user = frappe.get_doc("User", frappe.session.user)
	user.update(
		{"first_name": first_name, "last_name": last_name, "username": username, "user_image": user_image}
	)
	user.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def complete_onboarding() -> None:
	frappe.db.set_value("User", frappe.session.user, services.STATUS_FIELD, "Completed")


@frappe.whitelist()
def get_onboarding_state() -> OnboardingState:
	return services.onboarding_state(frappe.session.user)


@frappe.whitelist(methods=["POST"])
# The dashboard sends null for an empty logo or description.
def save_community(
	team_name: str, slug: str, logo: str | None = None, short_description: str | None = None
) -> str:
	return setup.save_community(frappe.session.user, team_name, slug, logo, short_description)


@frappe.whitelist(methods=["POST"])
def save_first_event(event: FirstEvent) -> str:
	return setup.save_first_event(event)
