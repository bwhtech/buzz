from datetime import datetime
from datetime import time as clock_time

from frappe.utils import get_time, getdate

from buzz.www.event.meta import event_time_zone


def event_countdown(event) -> dict | None:
	"""Start and end of the banner countdown, or None once the event is over."""
	# An event with no closing time runs to the end of its last day.
	# Whole seconds: JavaScript only promises to parse milliseconds.
	zone = event_time_zone(event)
	start_time = get_time(event.start_time) if event.start_time else clock_time.min
	end_time = get_time(event.end_time) if event.end_time else clock_time(23, 59, 59)
	starts_at = datetime.combine(getdate(event.start_date), start_time, zone)
	ends_at = datetime.combine(getdate(event.end_date or event.start_date), end_time, zone)
	if ends_at <= datetime.now(zone):
		return None
	return {"starts_at": starts_at.isoformat(), "ends_at": ends_at.isoformat()}
