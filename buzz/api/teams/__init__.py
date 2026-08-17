import frappe

from buzz.api.teams.schemas import TeamOption


@frappe.whitelist()
def get_my_teams() -> list[TeamOption]:
	"""Teams the session user belongs to, for the dashboard team switcher.

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

	return [TeamOption(**my_team) for my_team in my_teams]
