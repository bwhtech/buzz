import frappe
from frappe.utils import now_datetime

no_cache = 1


def get_context(context):
	context.sponsorship_events = available_events()
	requested = frappe.form_dict.get("event")
	if requested:
		for event in context.sponsorship_events:
			if requested in (str(event.name), event.event_route):
				frappe.local.flags.redirect_location = event.url
				raise frappe.Redirect


def available_events():
	rows = frappe.get_all(
		"Sponsor Enquiry Form",
		filters={"publish": 1, "event.is_published": 1},
		or_filters=[["auto_close_at", "is", "not set"], ["auto_close_at", ">=", now_datetime()]],
		fields=["event as name", "route as form_route", "event.title as title", "event.route as event_route"],
		order_by="`tabBuzz Event`.start_date",
	)
	for row in rows:
		row.url = f"/b/{row.event_route}/{row.form_route}"
	return rows
