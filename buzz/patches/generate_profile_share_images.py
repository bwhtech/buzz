import frappe

from buzz.events.profile_og_image import enqueue_generate


def execute():
	teams = frappe.get_all("Buzz Team", filters={"is_personal": 1}, pluck="name")
	if not teams:
		return
	published = set(
		frappe.get_all("Buzz Event", filters={"team": ("in", teams), "is_published": 1}, pluck="team")
	)
	for team in published:
		enqueue_generate(team)
