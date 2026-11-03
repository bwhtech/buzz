import frappe

from buzz.events.doctype.event_venue.event_venue import group_venue_name


def execute():
	"""Group venues were named after all their locations joined, which overflowed every place
	the name showed and the field's 140 characters."""
	for group in frappe.get_all("Event Venue", filters={"has_multiple_locations": 1}, pluck="name"):
		names = frappe.get_all(
			"Event Venue Location",
			filters={"parent": group, "parenttype": "Event Venue"},
			fields=["venue.venue_name as venue_name"],
			order_by="idx",
			pluck="venue_name",
		)
		if len(names) > 1:
			frappe.db.set_value(
				"Event Venue", group, "venue_name", group_venue_name(names), update_modified=False
			)
