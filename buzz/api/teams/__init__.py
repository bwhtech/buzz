import frappe

from buzz.api.teams import invitations, services
from buzz.api.teams.schemas import InviteOutcome, TeamOption, TeamOverview


@frappe.whitelist()
def get_my_teams() -> list[TeamOption]:
	"""Teams the session user belongs to, for the settings dialog.

	Reads past permissions on purpose: Buzz Team is readable by Event Manager only, while a
	Frontdesk or Viewer member still has to see the team they work in. Rows are filtered to
	the session user's own enabled memberships.
	"""
	membership = frappe.qb.DocType("Buzz Team Membership")
	team = frappe.qb.DocType("Buzz Team")

	my_teams = (
		frappe.qb.from_(membership)
		.inner_join(team)
		.on(team.name == membership.team)
		.select(team.name, team.team_name, team.logo, membership.team_role)
		.where((membership.user == frappe.session.user) & (membership.enabled == 1))
	).run(as_dict=True)

	return [TeamOption(**my_team, members=services.members_of(my_team.name)) for my_team in my_teams]


@frappe.whitelist()
def get_team_overview(team: str) -> TeamOverview:
	return services.team_overview(team)


@frappe.whitelist(methods=["POST"])
def remove_member(team: str, user: str) -> None:
	services.remove_member(team, user)


@frappe.whitelist(methods=["POST"])
def invite_members(team: str, invites: list[dict]) -> list[InviteOutcome]:
	return invitations.invite_members(team, invites)


@frappe.whitelist(methods=["POST"])
def update_team(team: str, team_name: str, logo: str | None = None) -> None:
	services.update_team(team, team_name, logo)
