import frappe


def execute():
	"""Event Venue names used to be the docname. `venue_name` now carries the label."""
	venue = frappe.qb.DocType("Event Venue")
	frappe.qb.update(venue).set(venue.venue_name, venue.name).where(
		(venue.venue_name.isnull()) | (venue.venue_name == "")
	).run()

	event = frappe.qb.DocType("Buzz Event")
	# Every venue still carries its label as the docname here, so the link value is the label.
	frappe.qb.update(event).set(event.venue_name, event.venue).where(
		(event.venue_name.isnull()) | (event.venue_name == "")
	).run()
