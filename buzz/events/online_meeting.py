from functools import cached_property
from urllib.parse import urlparse

import frappe
from frappe import _

MEETING_PLATFORMS = {
	"zoom.us": "Zoom",
	"meet.google.com": "Google Meet",
	"teams.microsoft.com": "Microsoft Teams",
	"teams.live.com": "Microsoft Teams",
}


class OnlineMeeting:
	"""Where a guest joins an online event.

	A guest's own Zoom registration link wins, then the organiser's link, then the shared link
	of the event's Zoom session. Zoom registers guests on paid accounts only, and with
	registration on the shared link opens Zoom's sign-up form first.
	"""

	def __init__(self, event, ticket=None):
		self.event = event
		self.ticket = ticket

	@property
	def is_online(self) -> bool:
		return self.event.medium == "Online"

	@cached_property
	def join_url(self) -> str | None:
		if not self.is_online:
			return None
		url = self.registration_url or self.event.meeting_link or self.zoom_session_url or ""
		# A line break would end a property early in the calendar invite.
		if urlparse(url).scheme not in ("http", "https") or any(char.isspace() for char in url):
			return None
		return url

	@cached_property
	def platform(self) -> str | None:
		# The link decides; a linked Zoom session only names the platform when there is no link.
		if not self.join_url:
			zoom_session = self.event.get("zoom_meeting") or self.event.get("zoom_webinar")
			return "Zoom" if self.is_online and zoom_session else None
		host = urlparse(self.join_url).hostname or ""
		return next(
			(
				name
				for domain, name in MEETING_PLATFORMS.items()
				if host == domain or host.endswith(f".{domain}")
			),
			None,
		)

	@property
	def label(self) -> str | None:
		if not self.is_online:
			return None
		return _("Online on {0}").format(self.platform) if self.platform else _("Online")

	@cached_property
	def registration_url(self) -> str | None:
		"""The guest's own Zoom link, which nobody else can use."""
		registration = self.ticket and self.ticket.get("zoom_session_registration")
		return (
			frappe.db.get_value("Zoom Session Registration", registration, "join_url")
			if registration
			else None
		)

	@cached_property
	def zoom_session_url(self) -> str | None:
		for doctype, fieldname in (("Zoom Meeting", "zoom_meeting"), ("Zoom Webinar", "zoom_webinar")):
			if self.event.get(fieldname):
				return frappe.db.get_value(doctype, self.event.get(fieldname), "zoom_link")
		return None
