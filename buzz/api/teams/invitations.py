import frappe
from frappe.core.api.user_invitation import invite_by_email

from buzz.api.teams.exceptions import CannotGrantOwnership, CannotManageMembers, UnknownTeamRole
from buzz.api.teams.schemas import InviteOutcome
from buzz.events.doctype.buzz_team_membership.buzz_team_membership import upsert_membership
from buzz.permissions import can_manage_members

# Where an invitee lands once they accept. The router sends a team member on to their events.
INVITE_REDIRECT_PATH = "/b/manage"


def invite_members(team: str, invites: list[dict]) -> list[InviteOutcome]:
	"""Put people on a team, by whichever route each of them needs.

	Someone who already has a User joins straight away; only a stranger gets an emailed
	invitation. Splitting the two is not a nicety: core's `invite_by_email` skips any
	address that ever accepted a buzz invitation, without regard to which team it was
	for, so inviting a colleague to a second team would silently do nothing.
	"""
	if not can_manage_members(team):
		CannotManageMembers.throw()

	# Every row is checked before any of them is acted on, so one bad role cannot leave
	# half a batch invited.
	for invite in invites:
		validate_role(invite["team_role"])

	return [invite_one(team, invite) for invite in invites]


def validate_role(team_role: str) -> None:
	if team_role == "Owner":
		CannotGrantOwnership.throw()
	if team_role not in assignable_roles():
		UnknownTeamRole.throw(team_role=team_role)


def assignable_roles() -> list[str]:
	"""The membership doctype's own options, minus the one nobody may be given."""
	options = frappe.get_meta("Buzz Team Membership").get_field("team_role").options
	return [role for role in options.split("\n") if role and role != "Owner"]


def invite_one(team: str, invite: dict) -> InviteOutcome:
	# User names are lowercased emails, so the lookup has to be too.
	email = invite["email"].strip().lower()
	team_role = invite["team_role"]

	# None means no such User; an existing one with a blank name still reads as "".
	full_name = frappe.db.get_value("User", email, "full_name")
	if full_name is not None:
		added = upsert_membership(team, email, team_role)
		return InviteOutcome(
			email=email,
			status="added" if added else "already_a_member",
			full_name=full_name,
		)

	invite_by_email(
		emails=email,
		roles=["Buzz User"],
		redirect_to_path=INVITE_REDIRECT_PATH,
		app_name="buzz",
		buzz_team=team,
		buzz_team_role=team_role,
	)
	return InviteOutcome(email=email, status="invited")
