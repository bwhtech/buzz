from datetime import UTC, datetime
from datetime import time as clock_time
from urllib.parse import urlencode

from frappe.utils import get_time, get_url, getdate

from buzz.events.doctype.event_venue.details import venue_details
from buzz.utils import ics_location
from buzz.www.event.meta import event_time_zone

STAMP = "%Y%m%dT%H%M%SZ"


class CalendarLinks:
	"""Links that open each calendar provider with the event filled in, and the fields for an .ics file."""

	def __init__(self, event):
		self.event = event
		zone = event_time_zone(event)
		start_time = get_time(event.start_time) if event.start_time else clock_time.min
		end_time = get_time(event.end_time) if event.end_time else clock_time(23, 59, 59)
		self.start = datetime.combine(getdate(event.start_date), start_time, zone).astimezone(UTC)
		end_date = getdate(event.end_date or event.start_date)
		self.end = datetime.combine(end_date, end_time, zone).astimezone(UTC)
		self.location = "" if event.medium == "Online" else ics_location(venue_details(event.venue))
		self.url = get_url(f"/events/{event.route}")

	@classmethod
	def for_event(cls, event) -> dict | None:
		return cls(event).as_dict() if event.start_date else None

	def as_dict(self) -> dict:
		return {
			"google": self.google(),
			"outlook": self.outlook(),
			"yahoo": self.yahoo(),
			"ics": {
				"title": self.event.title,
				"start": self.start.strftime(STAMP),
				"end": self.end.strftime(STAMP),
				"location": self.location,
				"url": self.url,
			},
		}

	def google(self) -> str:
		query = {
			"action": "TEMPLATE",
			"text": self.event.title,
			"dates": f"{self.start.strftime(STAMP)}/{self.end.strftime(STAMP)}",
			"details": self.url,
			"location": self.location,
		}
		return "https://calendar.google.com/calendar/render?" + urlencode(query)

	def outlook(self) -> str:
		query = {
			"path": "/calendar/action/compose",
			"rru": "addevent",
			"subject": self.event.title,
			"startdt": self.start.isoformat(),
			"enddt": self.end.isoformat(),
			"location": self.location,
			"body": self.url,
		}
		return "https://outlook.live.com/calendar/0/action/compose?" + urlencode(query)

	def yahoo(self) -> str:
		query = {
			"v": 60,
			"title": self.event.title,
			"st": self.start.strftime(STAMP),
			"et": self.end.strftime(STAMP),
			"in_loc": self.location,
			"desc": self.url,
		}
		return "https://calendar.yahoo.com/?" + urlencode(query)
