import frappe


def execute():
	"""Venues saved before geocoding have no city or country; fill them in the background."""
	frappe.enqueue("buzz.events.doctype.event_venue.geocode.geocode_all_venues", queue="long", timeout=3600)
