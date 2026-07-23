import frappe
from frappe.utils.data import get_datetime

from buzz.utils import get_time_zone_label


def execute():
	events = frappe.get_all(
		"Buzz Event",
		filters={
			"time_zone": ("is", "set"),
			"start_date": ("is", "set"),
			"start_time": ("is", "set"),
		},
		fields=["name", "time_zone", "start_date", "start_time"],
	)
	for event in events:
		event_start = get_datetime(f"{event.start_date} {event.start_time}")
		label = get_time_zone_label(event.time_zone, event_start)
		frappe.db.set_value("Buzz Event", event.name, "time_zone_label", label, update_modified=False)
