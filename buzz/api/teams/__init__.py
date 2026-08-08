import frappe

from buzz.api.teams.schemas import TeamOption


@frappe.whitelist()
def get_my_teams() -> list[TeamOption]:
	"""Teams the session user belongs to, for the dashboard team switcher.

	Reads past permissions on purpose: Buzz Team is readable by Event Manager only, while a
	Frontdesk or Viewer member still has to see the team they are looking at. Rows are
	filtered to the session user's own enabled memberships.
	"""
	memberships = frappe.get_all(
		"Buzz Team Membership",
		filters={"user": frappe.session.user, "enabled": 1},
		fields=["team", "team_role"],
		ignore_permissions=True,
	)
	if not memberships:
		return []

	teams = frappe.get_all(
		"Buzz Team",
		filters={"name": ("in", [membership.team for membership in memberships])},
		fields=["name", "team_name", "logo"],
		ignore_permissions=True,
	)
	team_by_name = {team.name: team for team in teams}

	return [
		TeamOption(**team_by_name[membership.team], team_role=membership.team_role)
		for membership in memberships
		if membership.team in team_by_name
	]
