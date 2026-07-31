import frappe

from buzz.events.doctype.buzz_team.buzz_team import create_default_team_for


def execute():
	"""Give every existing organiser a team, so nothing is left without a tenant."""
	managers = frappe.get_all(
		"Has Role",
		filters={"parenttype": "User", "role": "Event Manager"},
		pluck="parent",
	)
	enabled_managers = frappe.get_all(
		"User",
		filters={"name": ("in", managers), "enabled": 1},
		pluck="name",
	)

	for user in enabled_managers:
		create_default_team_for(user)
