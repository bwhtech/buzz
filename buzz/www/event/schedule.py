import frappe

from buzz.www.event.index import EventPage, not_found
from buzz.www.site_header import apply_site_context

no_cache = 1


def get_context(context):
	page = EventPage(frappe.form_dict.event_route)
	if not page.schedule:
		not_found()
	apply_site_context(context, page.event.theme)
	context.update(page.as_context())
	context.update(schedule=page.schedule, schedule_tracks=page.public_schedule.filter_tracks)
