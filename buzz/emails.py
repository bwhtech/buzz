from urllib.parse import urlencode, urlparse

import frappe
from frappe.utils import get_url

from buzz.events.doctype.event_venue.details import venue_details
from buzz.events.doctype.event_venue.map_image import LocationsMapImage
from buzz.events.online_meeting import OnlineMeeting
from buzz.utils import build_event_datetimes, get_time_zone_label

WORDMARK = "/assets/buzz/images/buzz-wordmark-dark.png"


def email_event_header(event) -> dict:
	start, _ = build_event_datetimes(event)
	label = get_time_zone_label(event.time_zone, start)
	details = venue_details(event.venue)
	url = get_url(f"/events/{event.route}") if event.is_published and event.route else None
	return frappe._dict(
		month=start.strftime("%b").upper(),
		day=start.day,
		title=event.title,
		start_time=f"{start.strftime('%-I:%M %p')} {label}".strip(),
		venue=event.get_venue_name() or OnlineMeeting(event).label,
		venue_map_url=details and details.map_link,
		url=url,
		banner_url=get_url(event.banner_image) if event.banner_image else None,
		**email_locations(details, url),
	)


def email_locations(details, event_url: str | None) -> dict:
	"""A grouped venue's places, and the event page link that opens them on its map."""
	if not (details and details.has_multiple_locations):
		return {"locations": [], "locations_url": None, "locations_map_url": None}
	map_url = LocationsMapImage(details.name, details.locations).url()
	return {
		"locations": details.locations,
		"locations_url": event_url and f"{event_url}#locations",
		"locations_map_url": map_url and get_url(map_url),
	}


def email_brand() -> dict:
	settings = frappe.get_cached_doc("Website Settings")
	site_logo = settings.banner_image or settings.app_logo
	return frappe._dict(
		logo=get_url(site_logo or WORDMARK),
		name=(settings.app_name if site_logo else None) or "Buzz",
	)


def is_full_document(html: str | None) -> bool:
	return bool(html) and html.lstrip().lower().startswith("<!doctype")


def send_message_email(title: str, message: str, event=None, **sendmail_kwargs) -> None:
	frappe.sendmail(
		template="message",
		args={"title": title, "message": message, "event_doc": event},
		raw_html=True,
		add_css=False,
		**sendmail_kwargs,
	)
