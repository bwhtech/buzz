import frappe
from frappe.utils import now_datetime

no_cache = 1


def get_context(context):
	context.sponsorship_events = available_events()
	requested = frappe.form_dict.get("event")
	if requested:
		for event in context.sponsorship_events:
			if requested in (str(event.name), event.route):
				frappe.local.flags.redirect_location = event.url
				raise frappe.Redirect


def available_events():
	form = frappe.qb.DocType("Sponsor Enquiry Form")
	event = frappe.qb.DocType("Buzz Event")
	rows = (
		frappe.qb.from_(form)
		.join(event)
		.on(form.event == event.name)
		.select(event.name, event.title, event.route, form.route.as_("form_route"))
		.where((form.publish == 1) & (event.is_published == 1))
		.where(form.auto_close_at.isnull() | (form.auto_close_at >= now_datetime()))
		.orderby(event.start_date)
		.run(as_dict=True)
	)
	for row in rows:
		row.url = f"/b/{row.route}/{row.form_route}"
	return rows
