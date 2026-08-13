import frappe

from buzz.api.teams.exceptions import NotATeamMember
from buzz.api.teams.schemas import TeamMember, TeamOverview
from buzz.permissions import team_role_of

TEAM_FIELDS = ("name", "team_name", "slug", "logo")


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
	)


def members_of(team: str) -> list[TeamMember]:
	membership = frappe.qb.DocType("Buzz Team Membership")
	user = frappe.qb.DocType("User")

	rows = (
		frappe.qb.from_(membership)
		.inner_join(user)
		.on(user.name == membership.user)
		.select(membership.user, membership.team_role, user.full_name, user.user_image)
		.where((membership.team == team) & (membership.enabled == 1))
		.orderby(user.full_name)
	).run(as_dict=True)

	return [TeamMember(**row) for row in rows]
