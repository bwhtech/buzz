# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.data import get_url

from buzz.events.doctype.buzz_event.buzz_event import RESERVED_EVENT_ROUTES

DEFAULT_TITLE = "Buzz Dashboard"
TITLE_SEPARATOR = " - "
MAX_DESCRIPTION_LENGTH = 160


def get_page_meta(app_path: str | None) -> dict:
	"""Return the browser title and social meta tags for a dashboard route.

	The whole dashboard is one SPA served from a single Jinja shell
	(www/dashboard.html), so the route has to be resolved here for crawlers and
	link previews to see anything other than the default title.
	"""
	segments = [segment for segment in (app_path or "").split("/") if segment]
	try:
		meta = resolve_meta(segments)
	except Exception:
		# This renders the shell for every dashboard route, so a bad title must
		# never take the whole SPA down with it.
		frappe.log_error("Failed to resolve dashboard page meta")
		meta = {}

	title = meta.get("title") or DEFAULT_TITLE
	image = meta.get("image")
	return {
		"title": title,
		"description": clean_description(meta.get("description")) or title,
		"image": get_url(image) if image else "",
	}


def resolve_meta(segments: list[str]) -> dict:
	if len(segments) == 2 and segments[0] == "register":
		event = get_published_event(segments[1])
		return get_event_meta(event, _("Register")) if event else {}

	if segments == ["event-proposal"]:
		# Not tied to an event: this is the form for proposing a new one.
		banner_title = frappe.db.get_single_value("Buzz Settings", "event_proposal_banner_title")
		return {"title": banner_title or _("Propose an Event")}

	# Mirrors the vue-router catch-all /<event>/<form>, matched last there too.
	if len(segments) == 2 and segments[0] not in RESERVED_EVENT_ROUTES:
		event = get_published_event(segments[0])
		if not event:
			return {}
		form_doctype = get_published_form_doctype(event.name, segments[1])
		return get_event_meta(event, _(form_doctype)) if form_doctype else {}

	return {}


def get_event_meta(event: frappe._dict, suffix: str) -> dict:
	return {
		"title": f"{event.title}{TITLE_SEPARATOR}{suffix}",
		"description": event.short_description,
		"image": event.meta_image or event.banner_image,
	}


def get_published_event(event_route: str) -> frappe._dict | None:
	# Filtering on is_published matters: this runs for Guests and db reads
	# bypass permissions, so an unpublished event would leak its title.
	return frappe.db.get_value(
		"Buzz Event",
		{"route": event_route, "is_published": 1},
		["name", "title", "short_description", "meta_image", "banner_image"],
		as_dict=True,
	)


def get_published_form_doctype(event: str, form_route: str) -> str | None:
	return frappe.db.get_value(
		"Buzz Event Form",
		{"parent": event, "parenttype": "Buzz Event", "route": form_route, "publish": 1},
		"form_doctype",
	)


def clean_description(description: str | None) -> str:
	text = " ".join((description or "").split())
	if len(text) > MAX_DESCRIPTION_LENGTH:
		text = text[:MAX_DESCRIPTION_LENGTH].rstrip() + "..."
	return text
