import frappe
from frappe.core.api.user_invitation import cancel_invitation, invite_by_email, resend_invitation

from buzz.api.teams.exceptions import CannotManageMembers, NoPendingInvite
from buzz.api.teams.schemas import InviteOutcome
from buzz.api.teams.services import validate_role
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


def resend_invite(team: str, email: str) -> None:
	"""Mail the invitation again. Core rotates the key, so the earlier link stops working."""
	resend_invitation(name=pending_invite(team, email), app_name="buzz")


def retract_invite(team: str, email: str) -> None:
	"""Cancel the invitation. Core mails the invitee that it was withdrawn."""
	cancel_invitation(name=pending_invite(team, email), app_name="buzz")


def pending_invite(team: str, email: str) -> str:
	"""The one pending buzz invitation for this address on this team.

	Core allows at most one pending invitation per address per app, so the pair is a key.
	Its own guards are app-wide rather than team-wide, which is why the team check lives here.
	"""
	if not can_manage_members(team):
		CannotManageMembers.throw()

	name = frappe.db.exists(
		"User Invitation",
		{"buzz_team": team, "email": email.strip().lower(), "status": "Pending", "app_name": "buzz"},
	)
	if not name:
		NoPendingInvite.throw(email=email)
	return name
