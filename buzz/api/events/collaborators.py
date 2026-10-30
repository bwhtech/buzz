import frappe
from frappe.rate_limiter import rate_limit

from buzz.api.events.exceptions import (
	AlreadyCollaborator,
	AlreadyOnTeam,
	CannotManageEvent,
	CollaboratorLoginRequired,
	CollaboratorWrongAccount,
	EventNotFound,
	InvalidCollaboratorInvitation,
	InvalidSectionAccess,
	UnknownCollaborator,
)
from buzz.api.schemas import APIResponse
from buzz.api.teams.schemas import InviteOutcome
from buzz.permissions import (
	EDIT,
	SECTIONS,
	VIEW,
	can_manage_members,
	get_section_access,
	team_role_of,
)

COLLABORATOR = "Buzz Event Collaborator"


class AcceptedInvitation(APIResponse):
	redirect_to: str


@frappe.whitelist()
def get_event_access(event: str) -> dict[str, str | None]:
	"""Section -> View | Edit | None for the session user."""
	return get_section_access(frappe.session.user, event)


@frappe.whitelist()
def has_collaborations() -> bool:
	return bool(frappe.db.exists(COLLABORATOR, {"user": frappe.session.user, "status": "Accepted"}))


@frappe.whitelist(methods=["POST"])
def invite_collaborators(event: str, invites: list[dict]) -> list[InviteOutcome]:
	team = managed_team(event)
	for invite in invites:
		validate_sections(invite)
	return [invite_one(event, team, invite) for invite in invites]


@frappe.whitelist(methods=["POST"])
def update_collaborator_access(event: str, email: str, sections: dict) -> None:
	managed_team(event)
	validate_sections(sections)
	row = existing_row(event, email)
	row.update(section_values(sections))
	row.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def revoke_collaborators(event: str, emails: list[str]) -> None:
	managed_team(event)
	for email in emails:
		existing_row(event, email).revoke()


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=60)
def accept_collaborator_invite(key: str) -> AcceptedInvitation:
	row = pending_invitation(key)
	is_new_user = not frappe.db.exists("User", row.email)
	user = create_user(row.email) if is_new_user else verified_user(row.email)
	row.accept(user.name if is_new_user else user)
	redirect_to = f"/b/manage/events/{row.event}"
	if is_new_user:
		redirect_to = start_session(user, redirect_to)
	return AcceptedInvitation(redirect_to=redirect_to)


def managed_team(event: str) -> str:
	team = frappe.db.get_value("Buzz Event", event, "team")
	if not team:
		EventNotFound.throw()
	if not can_manage_members(team):
		CannotManageEvent.throw()
	return team


def validate_sections(sections: dict) -> None:
	for section, level in section_values(sections).items():
		allowed = (VIEW, EDIT) if section == "details_access" else ("", VIEW, EDIT)
		if level not in allowed:
			InvalidSectionAccess.throw(section=section.removesuffix("_access"))


def section_values(sections: dict) -> dict:
	fieldnames = [f"{section}_access" for section in SECTIONS]
	return {fieldname: sections[fieldname] or "" for fieldname in fieldnames if fieldname in sections}


def existing_row(event: str, email: str):
	name = frappe.db.exists(COLLABORATOR, {"event": event, "email": email.strip().lower()})
	if not name:
		UnknownCollaborator.throw(email=email)
	return frappe.get_doc(COLLABORATOR, name)


def invite_one(event: str, team: str, invite: dict) -> InviteOutcome:
	email = invite["email"].strip().lower()
	if team_role_of(email, team):
		AlreadyOnTeam.throw(email=email)

	name = frappe.db.exists(COLLABORATOR, {"event": event, "email": email})
	row = frappe.get_doc(COLLABORATOR, name) if name else frappe.new_doc(COLLABORATOR)
	if row.status == "Accepted":
		AlreadyCollaborator.throw(email=email)

	row.update({"event": event, "email": email} | section_values(invite))
	row.issue_invitation(frappe.session.user)
	return InviteOutcome(email=email, status="invited")


def pending_invitation(key: str):
	name = frappe.db.get_value(
		COLLABORATOR, {"invite_key_hash": frappe.utils.sha256_hash(key or ""), "status": "Pending"}
	)
	if not name:
		InvalidCollaboratorInvitation.throw()

	row = frappe.get_doc(COLLABORATOR, name)
	# The inviter's authority is checked now, not only when they sent it.
	if row.is_expired or not can_manage_members(row.team, row.invited_by):
		InvalidCollaboratorInvitation.throw()
	return row


def verified_user(email: str) -> str:
	"""The key is not a login for an existing account, which may be privileged."""
	if frappe.session.user == "Guest":
		CollaboratorLoginRequired.throw(email=email)
	if frappe.session.user != email:
		CollaboratorWrongAccount.throw()
	return email


def create_user(email: str):
	user = frappe.new_doc("User")
	user.update(
		{
			"email": email,
			"first_name": email.split("@")[0].title(),
			"send_welcome_email": 0,
			"user_type": "System User",
		}
	)
	user.append_roles("Buzz User")
	return user.insert(ignore_permissions=True)


def start_session(user, redirect_to: str) -> str:
	"""A new person proved the inbox, so they are logged in, or sent to set a password first."""
	if frappe.get_system_settings("disable_user_pass_login"):
		log_in_as(user.name)
		return redirect_to
	return f"{user._reset_password()}&redirect_to={redirect_to}"


def log_in_as(user: str) -> None:
	frappe.local.login_manager.login_as(user)
