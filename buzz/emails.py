from urllib.parse import urlencode, urlparse

import frappe
from frappe.utils import get_url

from buzz.events.doctype.event_venue.details import venue_details
from buzz.events.online_meeting import OnlineMeeting
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
		venue=event.get_venue_name() or OnlineMeeting(event).label,
		venue_map_url=(details := venue_details(event.venue)) and details.map_link,
		url=get_url(f"/events/{event.route}") if event.is_published and event.route else None,
		banner_url=get_url(event.banner_image) if event.banner_image else None,
	)


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
