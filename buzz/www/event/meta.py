import textwrap
from datetime import datetime
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from frappe.utils import get_system_timezone, get_time, get_url, getdate

DESCRIPTION_LENGTH = 160
IMAGE_FIELDS = ("meta_image", "og_image", "banner_image", "card_image")


def plain_text(html: str | None) -> str:
	return BeautifulSoup(html or "", "html.parser").get_text(" ")


class EventMeta:
	"""Share and search metadata for an event page, built from the page context."""

	def __init__(self, event, page, context: dict):
		self.event = event
		self.page = page
		self.context = context

	def as_dict(self) -> dict:
		image = self.image()
		return {
			"title": f"{self.page.title} · {self.event.title}" if self.page else self.event.title,
			"description": self.description(),
			"image": image,
			"url": self.url(),
			"card": "summary_large_image" if image else "summary",
		}

	def url(self) -> str:
		return get_url(f"/events/{self.event.route}" + (f"/{self.page.route}" if self.page else ""))

	def description(self) -> str:
		text = self.event.short_description or plain_text(self.event.about)
		return textwrap.shorten(text, DESCRIPTION_LENGTH, placeholder="…")

	def image(self) -> str:
		# Crawlers get a 403 on private files, which drops the preview image silently
		urls = [self.event.get(field) for field in IMAGE_FIELDS]
		public = next((url for url in urls if url and not url.startswith("/private/")), None)
		return get_url(public) if public else ""

	def structured_data(self) -> dict | None:
		if self.page:
			return None
		image = self.image()
		data = {
			"@context": "https://schema.org",
			"@type": "Event",
			"name": self.event.title,
			"description": self.description(),
			"startDate": self.event_datetime(self.event.start_date, self.event.start_time),
			"endDate": self.end_datetime(),
			"eventAttendanceMode": self.attendance_mode(),
			"location": self.location(),
			"image": [image] if image else None,
			"organizer": self.organizer(),
			"offers": self.offers(),
			"url": self.url(),
		}
		return {key: value for key, value in data.items() if value}

	def event_datetime(self, date, time) -> str:
		if not time:
			return getdate(date).isoformat()
		zone = ZoneInfo(self.event.time_zone or get_system_timezone())
		return datetime.combine(getdate(date), get_time(time), zone).isoformat()

	def end_datetime(self) -> str | None:
		if not self.event.end_time:
			return None
		return self.event_datetime(self.event.end_date or self.event.start_date, self.event.end_time)

	def is_online(self) -> bool:
		return self.event.medium == "Online"

	def attendance_mode(self) -> str:
		mode = "Online" if self.is_online() else "Offline"
		return f"https://schema.org/{mode}EventAttendanceMode"

	def location(self) -> dict | None:
		# The canonical page, never the join link
		if self.is_online():
			return {"@type": "VirtualLocation", "url": self.url()}
		venue = self.context["venue"]
		return {"@type": "Place", "name": venue["name"], "address": venue["address"]} if venue else None

	def organizer(self) -> dict | None:
		hosts = self.context["hosts"]
		return {"@type": "Organization", "name": hosts[0].label, "url": get_url()} if hosts else None

	def offers(self) -> dict | None:
		register_url = self.context["register_url"]
		if not register_url or self.context["registrations_closed"]:
			return None
		return {"@type": "Offer", "url": get_url(register_url), "availability": "https://schema.org/InStock"}
