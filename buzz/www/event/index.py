from functools import cached_property
from itertools import groupby
from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.utils import (
	comma_sep,
	format_date,
	get_datetime,
	get_system_timezone,
	get_time,
	getdate,
	nowdate,
)

from buzz.api.booking.services import are_registrations_closed
from buzz.api.events.services import co_hosts_of, primary_host_of, registration_link
from buzz.events.countdown import event_countdown
from buzz.events.doctype.buzz_team.buzz_team import personal_team_owner, personal_teams_enabled
from buzz.events.doctype.event_venue.details import VenueLocation, venue_details
from buzz.events.doctype.sponsorship_tier.sponsorship_tier import default_price
from buzz.events.online_meeting import OnlineMeeting
from buzz.utils import datetime_in_time_zone, format_gmt_offset, get_time_zone_label
from buzz.www.event.banner_color import banner_color
from buzz.www.event.date_range import RANGE_SEPARATOR, EventDateRange, format_time
from buzz.www.event.dot_map import DotMap
from buzz.www.event.link_icons import LINK_ICON_PATHS
from buzz.www.event.meta import EventMeta, event_time_zone
from buzz.www.event.registration import ProposalCard, RegistrationCard
from buzz.www.event.venue_map import venue_map_url
from buzz.www.site_header import apply_site_context

no_cache = 1


def get_context(context):
	page = EventPage(frappe.form_dict.event_route)
	apply_site_context(context, page.event.theme)
	context.update(page.as_context())


def join_names(names: list[str]) -> str:
	return comma_sep(names, _("{0} and {1}"), add_quotes=False)


def format_day(date) -> str:
	return format_date(date, "EEE d MMM y")


def join_parts(parts: list, separator: str) -> str:
	return separator.join([part for part in parts if part])


def format_time_range(start, end) -> str:
	return join_parts([format_time(start), format_time(end)], RANGE_SEPARATOR)


def web_url(url: str | None) -> str | None:
	# Frappe's URL field check lets javascript: through
	return url if url and urlparse(url).scheme in ("http", "https") else None


def public_links(rows) -> list[dict]:
	return [
		{
			"label": row.label,
			"url": url,
			"icon_svg": LINK_ICON_PATHS.get(row.icon) or LINK_ICON_PATHS["link"],
		}
		for row in rows
		if (url := web_url(row.url))
	]


def host_page_url(team: str | None) -> str | None:
	"""A personal team links to its owner's profile, any other team to its published page."""
	if not team:
		return None
	row = frappe.db.get_value("Buzz Team", team, ["is_personal", "is_published", "route"], as_dict=True)
	if not row:
		return None
	if row.is_personal:
		owner = personal_team_owner(team)
		return f"/u/{owner.username}" if owner and owner.username and personal_teams_enabled() else None
	return f"/{row.route}" if row.is_published and row.route else None


def format_full_date(date) -> str:
	pattern = "EEEE, d MMMM" if date.year == getdate(nowdate()).year else "EEEE, d MMMM y"
	return format_date(date, pattern)


def not_found():
	frappe.throw(_("Page not found"), frappe.PageDoesNotExistError)


class EventPage:
	def __init__(self, route: str):
		# get_doc skips the team permission hooks, which would hide every event from a Guest
		name = frappe.db.get_value("Buzz Event", {"route": route, "is_published": 1})
		if not name:
			not_found()
		self.event = frappe.get_doc("Buzz Event", name)

	def as_context(self) -> dict:
		context = {
			"event": self.event,
			"banner_color": banner_color(self.event.banner_image),
			"event_date": self.event_date(),
			"date_range": EventDateRange(self.event).as_dict(),
			"timezone_label_with_offset": self.timezone_label_with_offset(),
			"timezone_label": self.timezone_label,
			"pages": self.pages(),
			"tabs": self.tabs(),
			"hosts": self.hosts(),
			"links": self.links(),
			"schedule": self.schedule,
			"speakers": self.speakers,
			"sponsor_tiers": self.sponsor_tiers,
			"venue": self.venue(),
			# Only the service is named; the link itself goes to guests once they register.
			"online_label": OnlineMeeting(self.event).label,
			"register_url": registration_link(self.event),
			"registrations_closed": are_registrations_closed(self.event),
			"registration": RegistrationCard(self.event).as_dict(),
			"proposal_card": ProposalCard(self.event).as_dict(),
			"countdown": event_countdown(self.event) if self.event.show_countdown else None,
			"manage_url": self.manage_url(),
		}
		meta = EventMeta(self.event, context)
		return context | {"meta": meta.as_dict(), "structured_data": meta.structured_data()}

	def manage_url(self) -> str | None:
		if frappe.has_permission("Buzz Event", "write", self.event):
			return f"/b/manage/events/{self.event.name}/details"

	def tabs(self) -> list[dict]:
		sections = [
			("about", _("About"), True),
			("schedule", _("Schedule"), self.schedule),
			("speakers", _("Speakers"), self.speakers),
			("sponsors", _("Sponsors"), self.sponsor_tiers),
		]
		return [{"key": key, "label": label} for key, label, content in sections if content]

	def pages(self) -> list[dict]:
		# Keyed by document name: the tab and its panel are siblings in the markup, so the
		# pair needs an id, and a page may be renamed without the tab changing.
		return frappe.get_all(
			"Additional Event Page",
			filters={"event": self.event.name, "is_published": 1},
			fields=["name as key", "title as label", "content"],
			order_by="display_order asc, creation asc",
		)

	def event_date(self) -> dict:
		start_date = getdate(self.event.start_date)
		return {
			"month": format_date(start_date, "MMM"),
			"day": start_date.day,
			"full_date": format_full_date(start_date),
			"time_range": join_parts([self.time_range(), self.timezone_label], " "),
		}

	def time_range(self) -> str:
		start_time, end_time = self.event.start_time, self.event.end_time
		end_date = getdate(self.event.end_date) if self.event.end_date else None
		if not end_date or end_date == getdate(self.event.start_date):
			return format_time_range(start_time, end_time)
		end_text = join_parts([format_date(end_date, "d MMM"), format_time(end_time)], ", ")
		return join_parts([format_time(start_time), end_text], RANGE_SEPARATOR)

	@cached_property
	def timezone_label(self) -> str:
		return self.event.time_zone_label or get_time_zone_label(self.time_zone, self.start_datetime)

	def timezone_label_with_offset(self) -> str:
		local_datetime = datetime_in_time_zone(self.time_zone, self.start_datetime)
		offset = format_gmt_offset(local_datetime) if local_datetime else ""
		if offset in ("", self.timezone_label):
			return self.timezone_label
		return f"{self.timezone_label} ({offset})"

	@property
	def time_zone(self) -> str:
		return self.event.time_zone or get_system_timezone()

	@property
	def start_datetime(self):
		return get_datetime(f"{self.event.start_date} {self.event.start_time or '00:00:00'}")

	def hosts(self) -> list:
		# The hosting team links to its public page, or a personal team to its owner's profile.
		primary = primary_host_of(self.event.team)
		hosts = [frappe._dict(primary.__json__(), url=host_page_url(self.event.team))] if primary else []
		return hosts + [frappe._dict(host.__json__(), url=None) for host in co_hosts_of(self.event.name)]

	def links(self) -> list[dict]:
		return public_links(self.event.external_links)

	@cached_property
	def schedule(self) -> list[dict]:
		talk_titles = self.talk_titles([row.talk for row in self.event.schedule if row.talk])
		talk_speakers = self.talk_speakers(list(talk_titles))
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
		talks = frappe.get_all(
			"Event Talk",
			filters={"name": ["in", talk_names], "event": self.event.name},
			fields=["name", "title"],
		)
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
			"role": join_parts([profile.designation, profile.company], ", "),
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
		for sponsor in sponsors:
			sponsor.website = web_url(sponsor.website)
		tiers = frappe.get_all(
			"Sponsorship Tier",
			filters={"event": self.event.name},
			fields=["name", "title", {"prices": ["price"]}],
			order_by="creation asc",
		)
		tiers.sort(key=default_price, reverse=True)
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
		details = self.event.medium != "Online" and venue_details(self.event.venue)
		if not details:
			return None
		venue = {
			"name": details.venue_name,
			"address": details.address,
			"link": details.map_link,
			"map_url": None,
			"locations": [],
			"dot_map": None,
		}
		if not details.has_multiple_locations:
			return venue | {"map_url": self.venue_map_url()}
		return venue | LocationsMap(details.locations).as_context()

	def venue_map_url(self) -> str | None:
		return venue_map_url(frappe.get_cached_doc("Event Venue", self.event.venue))


class LocationsMap:
	"""A grouped venue's locations, each with its pin on a dot map framed around them."""

	def __init__(self, locations: list[VenueLocation]):
		self.locations = locations
		self.pinned = [location for location in locations if location.latitude and location.longitude]
		coordinates = [(location.latitude, location.longitude) for location in self.pinned]
		self.dot_map = DotMap(coordinates) if coordinates else None

	def as_context(self) -> dict:
		return {
			"locations": [self.located(location) for location in self.locations],
			"dot_map": self.dot_map
			and {
				"view_box": str(self.dot_map.view),
				"dots_url": self.dot_map.dots_url,
				"dot_width": self.dot_map.dot_width,
			},
		}

	def located(self, location: VenueLocation) -> dict:
		pin = self.dot_map.pin(location.latitude, location.longitude) if location in self.pinned else None
		return {**location.__json__(), "pin": pin}
