import frappe

from buzz.events.doctype.event_check_in_zone.event_check_in_zone import create_default_zone


def execute():
	"""Give every event its default zone, and file existing check-ins under it."""
	events_with_zone = frappe.get_all("Event Check-in Zone", filters={"is_default": 1}, pluck="event")
	for event in frappe.get_all(
		"Buzz Event", filters={"name": ["not in", events_with_zone or [""]]}, pluck="name"
	):
		create_default_zone(event)

	frappe.db.sql(
		"""
		UPDATE `tabEvent Check In` checkin
		JOIN `tabEvent Check-in Zone` zone ON zone.event = checkin.event AND zone.is_default = 1
		SET checkin.zone = zone.name
		WHERE IFNULL(checkin.zone, '') = ''
		"""
	)
