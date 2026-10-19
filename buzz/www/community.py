import frappe
from frappe import _
from frappe.utils import add_days, get_url, today

from buzz.events.doctype.buzz_team.team_map import TeamMap
from buzz.events.doctype.buzz_team.team_page import group_by_day
from buzz.www.site_header import apply_site_context

no_cache = 1

# Day offset from today, time, title, venue, city, country, latitude, longitude.
PREVIEW_EVENTS = [
	(-13, "18:30", "Zine Swap", "Stardio Studio", "Berlin", "Germany", 52.5, 13.4),
	(-6, "19:00", "Claude Meetup BLR", "Samagata Foundation", "Bengaluru", "India", 12.97, 77.59),
	(3, "20:00", "Coffee @ Subko", "The Craftery by Subko", "Bengaluru", "India", 12.97, 77.59),
	(5, "18:00", "Night Market", "Markthalle Neun", "Berlin", "Germany", 52.5, 13.4),
	(12, "19:30", "Rust & Ramen", "Shibuya Stream", "Tokyo", "Japan", 35.66, 139.7),
]


def get_context(context):
	if not frappe.db.get_single_value("Buzz Settings", "enable_communities"):
		raise frappe.PageDoesNotExistError
	apply_site_context(context)
	context.update(CommunityLanding().as_context())


class CommunityLanding:
	"""The /community landing page. Its community page preview runs on made-up events."""

	def as_context(self) -> dict:
		cards = [self.card(*event) for event in PREVIEW_EVENTS]
		upcoming = [card for card in cards if card["date"] >= today()]
		past = [card for card in reversed(cards) if card["date"] < today()]
		team_map = TeamMap(upcoming, past).as_context()
		# Opens on every event: a visitor's own country would filter the preview down to one or two.
		team_map["page_data"]["time_zone_countries"] = {}
		description = _("Your community's page, events and followers — wherever in the world they gather.")
		return {
			"title": _("Communities"),
			"meta": frappe._dict(description=description, url=get_url("/community")),
			"upcoming_days": group_by_day(upcoming),
			"past_days": group_by_day(past),
			**team_map,
		}

	def card(self, offset, time, title, place, city, country, latitude, longitude) -> dict:
		return {
			"route": frappe.scrub(title),
			"date": str(add_days(today(), offset)),
			"title": title,
			"url": "#",
			"time": time,
			"host_names": "Stardio",
			"place": place,
			"is_attending": offset == 3,
			"city": city,
			"country": country,
			"latitude": latitude,
			"longitude": longitude,
		}
