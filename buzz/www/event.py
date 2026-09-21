from itertools import groupby

import frappe
from frappe import _
from frappe.utils import comma_sep, get_datetime, get_system_timezone, get_time, get_url, getdate
from frappe.website.doctype.website_settings.website_settings import get_website_settings

from buzz.api.booking.services import are_registrations_closed
from buzz.api.events.services import co_hosts_of, primary_host_of, registration_link
from buzz.utils import get_time_zone_label
from buzz.www.site_header import SiteHeader
from buzz.www.venue_map import venue_map_url

no_cache = 1
RANGE_SEPARATOR = " \u2013 "


def get_context(context):
	context.update(get_website_settings(context))
	context.update(EventPage(frappe.form_dict.event_route).as_context())
	context.update(SiteHeader().as_context())
	context.theme = event_page_theme()


def event_page_theme() -> str:
	themes = frappe.get_meta("Buzz Settings").get_options("event_page_theme").split("\n")
	theme = frappe.db.get_single_value("Buzz Settings", "event_page_theme")
	return theme if theme in themes else themes[0]


def join_names(names: list[str]) -> str:
	return comma_sep(names, _("{0} and {1}"), add_quotes=False)


def format_day(date) -> str:
	return getdate(date).strftime("%a %d %b %Y")


def format_time(time) -> str:
	return get_time(time).strftime("%H:%M") if time else ""


def format_time_range(start, end) -> str:
	return RANGE_SEPARATOR.join(filter(None, [format_time(start), format_time(end)]))


class EventPage:
	def __init__(self, route: str):
		# get_doc skips the team permission hooks, which would hide every event from a Guest
		name = frappe.db.get_value("Buzz Event", {"route": route, "is_published": 1})
		if not name:
			frappe.throw(_("Event not found"), frappe.PageDoesNotExistError)
		self.event = frappe.get_doc("Buzz Event", name)

	def as_context(self) -> dict:
		hosts = self.hosts()
		return {
			"event": self.event,
			"dates": self.dates(),
			"times": format_time_range(self.event.start_time, self.event.end_time),
			"timezone": self.timezone(),
			"hosts": hosts,
			"hosted_by": join_names([host.label for host in hosts]),
			"schedule": self.schedule(),
			"speakers": self.speakers(),
			"sponsor_tiers": self.sponsor_tiers(),
			"venue": self.venue(),
			"register_url": registration_link(self.event),
			"registrations_closed": are_registrations_closed(self.event),
			"meta": self.meta(),
		}

	def dates(self) -> str:
		start, end = self.event.start_date, self.event.end_date
		if not end or getdate(end) == getdate(start):
			return format_day(start)
		return f"{format_day(start)}{RANGE_SEPARATOR}{format_day(end)}"

	def timezone(self) -> dict:
		name = self.event.time_zone or get_system_timezone()
		event_start = get_datetime(f"{self.event.start_date} {self.event.start_time or '00:00:00'}")
		label = self.event.time_zone_label or get_time_zone_label(name, event_start)
		return {"name": name, "label": label}

	def hosts(self) -> list:
		hosts = [primary_host_of(self.event.team), *co_hosts_of(self.event.name)]
		return [host for host in hosts if host]

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
			order_by="price desc",
		)
		tier_order = [tier.name for tier in tiers] + [None]
		tier_titles = {tier.name: tier.title for tier in tiers}
		return [
			{
				"title": tier_titles.get(tier, ""),
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
			"url": get_url(f"/events/{self.event.route}"),
		}
