import frappe


def execute():
	"""Event Venue names used to be the docname. `venue_name` now carries the label."""
	venue = frappe.qb.DocType("Event Venue")
	frappe.qb.update(venue).set(venue.venue_name, venue.name).where(
		(venue.venue_name.isnull()) | (venue.venue_name == "")
	).run()
