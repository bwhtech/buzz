import frappe

from buzz.events.profile_og_image import enqueue_generate


def execute():
	# ponytail: one job per personal team; generate() skips those without a published event
	for team in frappe.get_all("Buzz Team", filters={"is_personal": 1}, pluck="name"):
		enqueue_generate(team)
