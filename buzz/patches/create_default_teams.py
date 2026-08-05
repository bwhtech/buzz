from collections import Counter

import frappe

from buzz.events.doctype.buzz_team.buzz_team import create_default_team_for
from buzz.events.doctype.buzz_team_membership.buzz_team_membership import upsert_membership


def execute():
	"""Put every existing organiser in one team, the way the site worked before teams existed.

	A team per manager would take every event away from everyone but its creator.
	"""
	managers = get_enabled_event_managers()
	if not managers:
		return

	owner = pick_owner(managers)
	team = create_default_team_for(owner).name
	for user in managers:
		if user != owner:
			upsert_membership(team, user, "Admin")


def get_enabled_event_managers() -> list[str]:
	"""Administrator is left out — it bypasses team permissions and owns no one's work."""
	managers = frappe.get_all(
		"Has Role",
		filters={"parenttype": "User", "role": "Event Manager"},
		pluck="parent",
	)
	return frappe.get_all(
		"User",
		filters=[
			["name", "in", managers],
			["name", "not in", ("Administrator", "Guest")],
			["enabled", "=", 1],
		],
		pluck="name",
	)


def pick_owner(managers: list[str]) -> str:
	"""The manager behind the most events. Ties, and a site with no events, go to the oldest account."""
	event_counts = Counter(frappe.get_all("Buzz Event", filters={"owner": ("in", managers)}, pluck="owner"))
	by_seniority = frappe.get_all(
		"User", filters={"name": ("in", managers)}, pluck="name", order_by="creation asc"
	)
	# max keeps the first of equal keys, so seniority is the tie-break.
	return max(by_seniority, key=event_counts.__getitem__)
