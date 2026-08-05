import frappe

from buzz.events.doctype.buzz_team_settings.buzz_team_settings import create_team_settings


def execute():
	"""Seed settings for teams created before Buzz Team Settings existed."""
	for team in frappe.get_all("Buzz Team", pluck="name"):
		create_team_settings(team)
