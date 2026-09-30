from collections import Counter
from datetime import datetime
from urllib.parse import quote

import frappe
from frappe import _
from frappe.query_builder import Order
from frappe.query_builder.functions import Count
from frappe.utils import (
	add_days,
	get_datetime_in_timezone,
	get_system_timezone,
	get_time,
	get_url,
	getdate,
	today,
)

from buzz.www.event.index import format_day, not_found
from buzz.www.site_header import apply_site_context

no_cache = 1
LISTING_LIMIT = 60
FEATURED_LIMIT = 3
POPULAR_LIMIT = 8
CARD_FIELDS = ["title", "route", "start_date", "medium", "venue_name", "card_image", "banner_image"]
TIME_FIELDS = ["start_time", "end_date", "end_time", "time_zone"]


def get_context(context):
	apply_site_context(context)
	category_slug = frappe.form_dict.category
	page = EventListing(category_slug) if category_slug else DiscoverPage()
	context.update(page.as_context())
	context.show_hosting_banner = hosting_banner_visible(context.is_guest)


def hosting_banner_visible(is_guest: bool) -> bool:
	return is_guest and bool(frappe.db.get_single_value("Buzz Settings", "show_hosting_banner"))


def upcoming_filters() -> dict:
	# A day of slack for events in timezones behind the site's; exclude_ended_events makes the exact cut.
	return {"is_published": 1, "route": ["is", "set"], "end_date": [">=", add_days(today(), -1)]}


def current_time_in_event_timezone(event) -> datetime:
	return get_datetime_in_timezone(event.time_zone or get_system_timezone()).replace(tzinfo=None)


def has_started(event) -> bool:
	return datetime.combine(
		getdate(event.start_date), get_time(event.start_time)
	) <= current_time_in_event_timezone(event)


def has_ended(event) -> bool:
	return datetime.combine(
		getdate(event.end_date), get_time(event.end_time)
	) < current_time_in_event_timezone(event)


def exclude_ended_events(events: list) -> list:
	return [event for event in events if not has_ended(event)]


def enabled_categories() -> list:
	return frappe.get_all(
		"Event Category",
		filters={"enabled": 1, "slug": ["is", "set"]},
		fields=["name", "slug", "icon_svg"],
		order_by="name",
	)


def icon_url(icon_svg: str | None) -> str:
	# Loaded through <img>, where browsers do not run scripts inside the SVG.
	return f"data:image/svg+xml,{quote(icon_svg)}" if icon_svg else ""


def event_card(event) -> dict:
	return {
		"title": event.title,
		"url": f"/events/{event.route}",
		"date": format_day(event.start_date),
		"is_live": has_started(event) and not has_ended(event),
		"place": _("Online") if event.medium == "Online" else event.venue_name,
		"image": event.card_image or event.banner_image,
	}


class DiscoverPage:
	def as_context(self) -> dict:
		return {
			"title": _("Discover Events"),
			"category": None,
			"featured_events": [event_card(event) for event in self.featured_events()],
			"popular_events": [event_card(event) for event in self.popular_events()],
			"categories": self.categories(),
			"meta": {
				"url": get_url("/events"),
				"description": _("Find popular events and browse by category."),
			},
		}

	def featured_events(self) -> list:
		events = frappe.get_all(
			"Buzz Event",
			filters=upcoming_filters() | {"is_featured": 1},
			fields=CARD_FIELDS + TIME_FIELDS,
			order_by="start_date asc",
			limit=FEATURED_LIMIT,
		)
		return exclude_ended_events(events)

	def popular_events(self, limit: int = POPULAR_LIMIT) -> list:
		event = frappe.qb.DocType("Buzz Event")
		ticket = frappe.qb.DocType("Event Ticket")
		query = frappe.qb.get_query(
			"Buzz Event",
			fields=CARD_FIELDS + TIME_FIELDS,
			filters=upcoming_filters() | {"is_featured": 0},
		)
		events = (
			query.left_join(ticket)
			.on((ticket.event == event.name) & (ticket.docstatus == 1))
			.groupby(event.name)
			.orderby(Count(ticket.name), order=Order.desc)
			.orderby(event.start_date)
			.limit(limit)
		).run(as_dict=True)
		return sorted(exclude_ended_events(events), key=lambda event: event.start_date, reverse=True)

	def categories(self) -> list[dict]:
		counts = self.event_counts()
		return [
			{
				"name": category.name,
				"slug": category.slug,
				"icon_url": icon_url(category.icon_svg),
				"event_count": counts.get(category.name, 0),
			}
			for category in enabled_categories()
		]

	def event_counts(self) -> dict[str, int]:
		events = frappe.get_all("Buzz Event", filters=upcoming_filters(), fields=["category", *TIME_FIELDS])
		return Counter(event.category for event in exclude_ended_events(events))


class EventListing:
	def __init__(self, category_slug: str):
		self.category = self.load_category(category_slug)

	def load_category(self, slug: str) -> frappe._dict:
		category = frappe.db.get_value(
			"Event Category",
			{"slug": slug, "enabled": 1},
			["name", "slug", "description", "banner_image"],
			as_dict=True,
		)
		return category or not_found()

	def as_context(self) -> dict:
		return {
			"title": self.category.name,
			"category": self.category,
			"categories": enabled_categories(),
			"events": [event_card(event) for event in self.events()],
			"meta": {
				"url": get_url(f"/events?category={quote(self.category.slug)}"),
				"description": self.category.description or "",
			},
		}

	def events(self) -> list:
		events = frappe.get_all(
			"Buzz Event",
			filters=upcoming_filters() | {"category": self.category.name},
			fields=CARD_FIELDS + TIME_FIELDS,
			order_by="start_date asc",
			limit=LISTING_LIMIT,
		)
		return exclude_ended_events(events)
