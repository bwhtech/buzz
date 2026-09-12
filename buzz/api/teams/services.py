import frappe
from frappe.query_builder import Case

from buzz.api.teams.exceptions import (
	CannotEditTeam,
	CannotGrantOwnership,
	CannotManageMembers,
	NotATeamMember,
	UnknownTeamRole,
)
from buzz.api.teams.schemas import TeamInvite, TeamMember, TeamOverview
from buzz.permissions import can_manage_members, team_role_of

TEAM_FIELDS = ("name", "team_name", "slug", "logo")


def validate_role(team_role: str) -> None:
	if team_role == "Owner":
		CannotGrantOwnership.throw()
	if team_role not in assignable_roles():
		UnknownTeamRole.throw(team_role=team_role)


def assignable_roles() -> list[str]:
	"""The membership doctype's own options, minus the one nobody may be given."""
	options = frappe.get_meta("Buzz Team Membership").get_field("team_role").options
	return [role for role in options.split("\n") if role and role != "Owner"]


def team_overview(team: str) -> TeamOverview:
	"""Everything the team dashboard shows about one team.

	Reads past permissions like `get_my_teams`: Buzz Team is readable by Event Manager
	only, while a Frontdesk or Viewer member still works inside the team. Membership is
	the authorization.
	"""
	role = team_role_of(frappe.session.user, team)
	if not role:
		NotATeamMember.throw()

	details = frappe.db.get_value("Buzz Team", team, TEAM_FIELDS, as_dict=True)
	if not details:
		NotATeamMember.throw()

	return TeamOverview(
		**details,
		my_role=role,
		members=members_of(team),
		invites=pending_invites_for(team),
	)


def members_of(team: str) -> list[TeamMember]:
	membership = frappe.qb.DocType("Buzz Team Membership")
	user = frappe.qb.DocType("User")

	# A team can hold several Owners, so this is a role bucket rather than a single row.
	owner_first = Case().when(membership.team_role == "Owner", 0).else_(1)

	rows = (
		frappe.qb.from_(membership)
		.inner_join(user)
		.on(user.name == membership.user)
		.select(membership.user, membership.team_role, user.full_name, user.user_image)
		.where((membership.team == team) & (membership.enabled == 1))
		.orderby(owner_first)
		.orderby(user.full_name)
	).run(as_dict=True)

	return [TeamMember(**row) for row in rows]


def pending_invites_for(team: str) -> list[TeamInvite]:
	"""Invitations still waiting on their recipient.

	App-scoped as well as team-scoped: `User Invitation` is shared with every other
	installed app, and only buzz's own rows carry a team.
	"""
	rows = frappe.db.get_all(
		"User Invitation",
		filters={"buzz_team": team, "status": "Pending", "app_name": "buzz"},
		fields=["email", "buzz_team_role as team_role"],
		order_by="creation asc",
	)

	return [TeamInvite(**row) for row in rows]


def remove_member(team: str, user: str) -> None:
	"""Take a member off a team by disabling their membership.

	Disabled rather than deleted: `upsert_membership` re-enables the same row if they are
	ever invited back, and the history survives. An Owner row refuses to be disabled in the
	membership controller, so ownership needs no check here.
	"""
	if not can_manage_members(team):
		CannotManageMembers.throw()

	name = frappe.db.exists("Buzz Team Membership", {"team": team, "user": user, "enabled": 1})
	if not name:
		NotATeamMember.throw()

	membership = frappe.get_doc("Buzz Team Membership", name)
	membership.enabled = 0
	# Event Manager holds no write permission on the membership doctype, so the guard above
	# is the authorization — the same shape as the Desk add-members flow.
	membership.save(ignore_permissions=True)


def change_role(team: str, user: str, team_role: str) -> None:
	"""Move a member to another role.

	Ownership is out of reach from both ends: `validate_role` refuses it as a target, and
	the membership controller refuses to take it away from the row that holds it.
	"""
	if not can_manage_members(team):
		CannotManageMembers.throw()
	validate_role(team_role)

	name = frappe.db.exists("Buzz Team Membership", {"team": team, "user": user, "enabled": 1})
	if not name:
		NotATeamMember.throw()

	membership = frappe.get_doc("Buzz Team Membership", name)
	membership.team_role = team_role
	# Same shape as `remove_member`: the guard above is the authorization, since Event
	# Manager holds no write permission on the membership doctype.
	membership.save(ignore_permissions=True)


def remove_members(team: str, users: list[str]) -> None:
	"""Take several members off a team at once.

	One request is one transaction, so a refusal on any of them takes the whole batch
	back out — the roster is never left half-changed.
	"""
	for user in users:
		remove_member(team, user)


def change_roles(team: str, users: list[str], team_role: str) -> None:
	"""Move several members to the same role, all-or-nothing like `remove_members`."""
	for user in users:
		change_role(team, user, team_role)


def update_team(team: str, team_name: str, logo: str | None) -> None:
	"""Rename a team or change its logo.

	Owner/Admin, the rule `team_doc_has_permission` applies to a write. Desk write on Buzz
	Team is System Manager only, so the guard here is the authorization and the save skips
	the doctype check — the same shape as `remove_member`.
	"""
	if not can_manage_members(team):
		CannotEditTeam.throw()

	team_name = team_name.strip()
	if not team_name:
		frappe.throw(frappe._("Team name is required"))

	doc = frappe.get_doc("Buzz Team", team)
	doc.team_name = team_name
	doc.logo = logo or None
	doc.save(ignore_permissions=True)
