from functools import cached_property
from itertools import groupby

import frappe
from frappe import _
from frappe.utils import (
	comma_sep,
	format_date,
	get_datetime,
	get_system_timezone,
	get_time,
	get_url,
	getdate,
	nowdate,
)

from buzz.api.booking.services import are_registrations_closed
from buzz.api.events.services import co_hosts_of, primary_host_of, registration_link
from buzz.utils import get_time_zone_label
from buzz.www.site_header import apply_site_context
from buzz.www.venue_map import venue_map_url

no_cache = 1
RANGE_SEPARATOR = " \u2013 "


def get_context(context):
	page = EventPage(frappe.form_dict.event_route, frappe.form_dict.page_route)
	apply_site_context(context, page.event.theme)
	context.update(page.as_context())


def join_names(names: list[str]) -> str:
	return comma_sep(names, _("{0} and {1}"), add_quotes=False)


def format_day(date) -> str:
	return format_date(date, "EEE d MMM y")


def format_time(time) -> str:
	return get_time(time).strftime("%H:%M") if time else ""


def format_time_range(start, end) -> str:
	return RANGE_SEPARATOR.join(filter(None, [format_time(start), format_time(end)]))


def format_full_date(date) -> str:
	pattern = "EEEE, d MMMM" if date.year == getdate(nowdate()).year else "EEEE, d MMMM y"
	return format_date(date, pattern)


def not_found():
	frappe.throw(_("Page not found"), frappe.PageDoesNotExistError)


class EventPage:
	def __init__(self, route: str, page_route: str | None = None):
		# get_doc skips the team permission hooks, which would hide every event from a Guest
		name = frappe.db.get_value("Buzz Event", {"route": route, "is_published": 1})
		if not name:
			not_found()
		self.event = frappe.get_doc("Buzz Event", name)
		self.page = self.load_page(page_route) if page_route else None

	def load_page(self, page_route: str) -> frappe._dict:
		page = frappe.db.get_value(
			"Additional Event Page",
			{"event": self.event.name, "route": page_route, "is_published": 1},
			["title", "route", "content"],
			as_dict=True,
		)
		if not page:
			not_found()
		return page

	def as_context(self) -> dict:
		return {
			"event": self.event,
			"event_date": self.event_date(),
			"timezone": self.timezone(),
			"page": self.page,
			"pages": self.pages(),
			"tabs": self.tabs(),
			"hosts": self.hosts(),
			"schedule": self.schedule,
			"speakers": self.speakers,
			"sponsor_tiers": self.sponsor_tiers,
			"venue": self.venue(),
			"register_url": registration_link(self.event),
			"registrations_closed": are_registrations_closed(self.event),
			"meta": self.meta(),
		}

	def tabs(self) -> list[dict]:
		sections = [
			("about", _("About"), True),
			("schedule", _("Schedule"), self.schedule),
			("speakers", _("Speakers"), self.speakers),
			("sponsors", _("Sponsors"), self.sponsor_tiers),
		]
		return [{"key": key, "label": label} for key, label, content in sections if content]

	def pages(self) -> list[dict]:
		return frappe.get_all(
			"Additional Event Page",
			filters={"event": self.event.name, "is_published": 1, "route": ["is", "set"]},
			fields=["title", "route"],
			order_by="creation",
		)

	def event_date(self) -> dict:
		start_date = getdate(self.event.start_date)
		return {
			"month": format_date(start_date, "MMM"),
			"day": start_date.day,
			"full_date": format_full_date(start_date),
			"time_range": " ".join(filter(None, [self.time_range(), self.timezone()["label"]])),
		}

	def time_range(self) -> str:
		start_time, end_time = self.event.start_time, self.event.end_time
		end_date = getdate(self.event.end_date) if self.event.end_date else None
		if not end_date or end_date == getdate(self.event.start_date):
			return format_time_range(start_time, end_time)
		end_text = ", ".join(filter(None, [format_date(end_date, "d MMM"), format_time(end_time)]))
		return RANGE_SEPARATOR.join(filter(None, [format_time(start_time), end_text]))

	def timezone(self) -> dict:
		name = self.event.time_zone or get_system_timezone()
		event_start = get_datetime(f"{self.event.start_date} {self.event.start_time or '00:00:00'}")
		label = self.event.time_zone_label or get_time_zone_label(name, event_start)
		return {"name": name, "label": label}

	def hosts(self) -> list:
		hosts = [primary_host_of(self.event.team), *co_hosts_of(self.event.name)]
		return [host for host in hosts if host]

	@cached_property
	def schedule(self) -> list[dict]:
		talk_names = [row.talk for row in self.event.schedule if row.talk]
		talk_titles = self.talk_titles(talk_names)
		talk_speakers = self.talk_speakers(talk_names)
		rows = sorted(self.event.schedule, key=lambda row: (getdate(row.date), get_time(row.start_time)))
		return [
			{
				"day": format_day(date),
				"rows": [self.schedule_row(row, talk_titles, talk_speakers) for row in day_rows],
			}
			for date, day_rows in groupby(rows, key=lambda row: row.date)
		]

	def schedule_row(self, row, talk_titles: dict, talk_speakers: dict) -> dict:
		return {
			"time": format_time_range(row.start_time, row.end_time),
			"title": talk_titles.get(row.talk) or row.description or _(row.type),
			"speakers": talk_speakers.get(row.talk, ""),
		}

	def talk_titles(self, talk_names: list[str]) -> dict:
		talks = frappe.get_all("Event Talk", filters={"name": ["in", talk_names]}, fields=["name", "title"])
		return {str(talk.name): talk.title for talk in talks}

	def talk_speakers(self, talk_names: list[str]) -> dict:
		rows = frappe.get_all(
			"Talk Speaker",
			filters={"parenttype": "Event Talk", "parent": ["in", talk_names]},
			fields=["parent", "speaker"],
			order_by="idx",
		)
		names = self.speaker_names([row.speaker for row in rows])
		speakers = {}
		for row in rows:
			speakers.setdefault(row.parent, []).append(names.get(row.speaker, row.speaker))
		return {talk: join_names(labels) for talk, labels in speakers.items()}

	def speaker_names(self, profiles: list[str]) -> dict:
		rows = frappe.get_all(
			"Speaker Profile", filters={"name": ["in", profiles]}, fields=["name", "display_name"]
		)
		return {str(row.name): row.display_name for row in rows}

	@cached_property
	def speakers(self) -> list[dict]:
		profiles = [row.speaker for row in self.event.featured_speakers]
		rows = frappe.get_all(
			"Speaker Profile",
			filters={"name": ["in", profiles]},
			fields=["name", "display_name", "designation", "company", "display_image"],
		)
		by_name = {str(row.name): row for row in rows}
		return [self.speaker(by_name[profile]) for profile in profiles if profile in by_name]

	def speaker(self, profile) -> dict:
		return {
			"name": profile.display_name,
			"role": ", ".join(filter(None, [profile.designation, profile.company])),
			"image": profile.display_image,
		}

	@cached_property
	def sponsor_tiers(self) -> list[dict]:
		sponsors = frappe.get_all(
			"Event Sponsor",
			filters={"event": self.event.name},
			fields=["company_name", "company_logo", "website", "tier"],
			order_by="creation",
		)
		tiers = frappe.get_all(
			"Sponsorship Tier",
			filters={"event": self.event.name},
			fields=["name", "title"],
			order_by="price desc, creation asc",
		)
		tier_order = [tier.name for tier in tiers] + [None]
		tier_titles = {tier.name: tier.title for tier in tiers}
		return [
			{
				"title": tier_titles.get(tier) or _("Other"),
				"sponsors": [sponsor for sponsor in sponsors if sponsor.tier == tier],
			}
			for tier in tier_order
			if any(sponsor.tier == tier for sponsor in sponsors)
		]

	def venue(self) -> dict | None:
		if self.event.medium == "Online" or not self.event.venue:
			return None
		venue = frappe.db.get_value(
			"Event Venue",
			self.event.venue,
			["name", "address", "type", "google_maps_embed_code", "latitude", "longitude"],
			as_dict=True,
		)
		return (
			{"name": venue.name, "address": venue.address, "map_url": venue_map_url(venue)} if venue else None
		)

	def meta(self) -> dict:
		image = self.event.meta_image or self.event.banner_image or self.event.card_image
		return {
			"description": self.event.short_description or "",
			"image": get_url(image) if image else "",
			"url": get_url(f"/events/{self.event.route}" + (f"/{self.page.route}" if self.page else "")),
		}
