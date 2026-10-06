from collections import Counter

import frappe
import pytz
from frappe.utils import today


def country_time_zones(country) -> list[str]:
	# Frappe's list misses some zones, Svalbard's Arctic/Longyearbyen among them.
	return (country.time_zones or "").split() or pytz.country_timezones.get((country.code or "").upper(), [])


class TeamMap:
	"""Map pins, region chips and calendar data for a team page, from its event cards."""

	def __init__(self, upcoming: list[dict], past: list[dict]):
		self.upcoming = upcoming
		self.past = past

	def as_context(self) -> dict:
		return {
			"has_pins": any(event["latitude"] is not None for event in self.upcoming),
			"countries": self.country_counts(),
			"upcoming_count": len(self.upcoming),
			"page_data": {
				"upcoming": self.upcoming,
				"past": self.past,
				"today": today(),
				"time_zone_countries": self.time_zone_countries(),
			},
		}

	def countries(self) -> list[str]:
		return [event["country"] for event in self.upcoming if event["country"]]

	def country_counts(self) -> list[dict]:
		counts = sorted(Counter(self.countries()).items(), key=lambda item: (-item[1], item[0]))
		return [{"name": name, "count": count} for name, count in counts]

	def time_zone_countries(self) -> dict[str, str]:
		countries = set(self.countries())
		if not countries:
			return {}
		rows = frappe.get_all(
			"Country", filters={"name": ["in", list(countries)]}, fields=["name", "code", "time_zones"]
		)
		return {zone: row.name for row in rows for zone in country_time_zones(row)}
