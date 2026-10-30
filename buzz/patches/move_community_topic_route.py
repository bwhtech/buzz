import frappe


def execute():
	"""The Community topic's /community route now serves the community landing page."""
	frappe.db.set_value("Event Topic", {"route": "community"}, "route", "community-events")
