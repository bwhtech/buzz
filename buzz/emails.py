from urllib.parse import urlencode, urlparse

import frappe
from frappe.utils import get_url

from buzz.utils import build_event_datetimes, get_time_zone_label

WORDMARK = "/assets/buzz/images/buzz-wordmark-dark.png"


def email_event_header(event) -> dict:
	start, _ = build_event_datetimes(event)
	label = get_time_zone_label(event.time_zone, start)
	return frappe._dict(
		month=start.strftime("%b").upper(),
		day=start.day,
		title=event.title,
		start_time=f"{start.strftime('%-I:%M %p')} {label}".strip(),
		venue=event.get_venue_name(),
		venue_map_url=venue_map_url(event.venue),
		url=get_url(f"/events/{event.route}") if event.is_published and event.route else None,
		banner_url=get_url(event.banner_image) if event.banner_image else None,
	)


def venue_map_url(venue: str | None) -> str | None:
	venue = venue and frappe.db.get_value(
		"Event Venue",
		venue,
		["venue_name", "address", "latitude", "longitude", "google_place_id", "map_link"],
		as_dict=True,
	)
	if not venue:
		return None
	# The organiser's own link wins. Pasted embed code is markup, not somewhere to go.
	if urlparse(venue.map_link or "").scheme in ("http", "https"):
		return venue.map_link
	if venue.google_place_id:
		place = {"api": 1, "query": venue.venue_name, "query_place_id": venue.google_place_id}
		return f"https://www.google.com/maps/search/?{urlencode(place)}"
	query = f"{venue.latitude},{venue.longitude}" if venue.latitude and venue.longitude else venue.address
	return f"https://www.google.com/maps/search/?{urlencode({'api': 1, 'query': query})}" if query else None


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
