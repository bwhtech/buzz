from collections import defaultdict
from datetime import datetime

import frappe
from frappe.utils import today
from pypika.terms import ExistsCriterion, ValueWrapper

from buzz.api.events.exceptions import ZoneNotFound
from buzz.api.events.schemas import ZoneOption, ZoneStatus
from buzz.events.doctype.event_check_in_zone.event_check_in_zone import (
	ONCE_PER_EVENT,
	enabled_zones,
)


class GuestZones:
	"""The event's enabled check-in zones, and who has checked in at each."""

	def __init__(self, event: str, load_counts: bool = True):
		self.event = str(event)
		self.zones = enabled_zones(self.event)
		self.zones_by_name = {str(zone.name): zone for zone in self.zones}
		self.ticket_types = self.zone_ticket_types()
		self.counts_by_zone, self._any_zone_count = (
			zone_checkin_counts(self.event, self.zones) if load_counts and self.zones else ({}, 0)
		)
		self.page_arrivals: defaultdict[str, dict[str, datetime]] = defaultdict(dict)

	def zone_ticket_types(self) -> dict[str, set[str]]:
		if not self.zones:
			return defaultdict(set)
		link = frappe.qb.DocType("Event Check-in Zone Ticket Type")
		rows = (
			frappe.qb.from_(link)
			.select(link.parent, link.ticket_type)
			.where(link.parent.isin([zone.name for zone in self.zones]))
		).run(as_dict=True)
		types = defaultdict(set)
		for row in rows:
			types[str(row.parent)].add(str(row.ticket_type))
		return types

	def resolve_zone(self, zone: str | None) -> str:
		if zone:
			match = next((row.name for row in self.zones if str(row.name) == str(zone)), None)
		else:
			match = next((row.name for row in self.zones if row.is_default), None)
		if not match:
			ZoneNotFound.throw()
		return str(match)

	def load_page_arrivals(self, tickets: list[str]) -> None:
		if not tickets or not self.zones:
			self.page_arrivals = defaultdict(dict)
			return
		self.page_arrivals = ticket_zone_arrivals(self.event, tickets, self.zones_by_name)

	def checked_in_count(self, zone: str) -> int:
		return self.counts_by_zone.get(str(zone), 0)

	def checked_in_criterion(self, zone: str, ticket_table, is_checked_in: bool):
		zone_row = self.zones_by_name[str(zone)]
		checkin = frappe.qb.DocType("Event Check In")
		condition = (
			(checkin.event == self.event)
			& (checkin.docstatus == 1)
			& (checkin.zone == str(zone_row.name))
			& (checkin.ticket == ticket_table.name)
		)
		if zone_row.repeat_rule != ONCE_PER_EVENT:
			condition = condition & (checkin.date == today())
		criterion = ExistsCriterion(frappe.qb.from_(checkin).select(ValueWrapper(1)).where(condition))
		return criterion if is_checked_in else criterion.negate()

	def allows(self, zone: str, ticket_type: str | None) -> bool:
		allowed = self.ticket_types.get(zone)
		return not allowed or str(ticket_type) in allowed

	def statuses(self, ticket: str, ticket_type: str | None) -> list[ZoneStatus]:
		return [
			ZoneStatus(
				name=zone.name,
				title=zone.title,
				allowed=self.allows(zone.name, ticket_type),
				checked_in_at=self.page_arrivals[str(zone.name)].get(ticket),
			)
			for zone in self.zones
		]

	def options(self, ticket_counts: dict[str, int] | None = None) -> list[ZoneOption]:
		total = sum(ticket_counts.values()) if ticket_counts is not None else None
		return [
			ZoneOption(
				name=zone.name,
				title=zone.title,
				is_default=bool(zone.is_default),
				checked_in=self.counts_by_zone.get(str(zone.name), 0),
				eligible=self.eligible(zone.name, ticket_counts, total),
			)
			for zone in self.zones
		]

	def eligible(
		self, zone: str, ticket_counts: dict[str, int] | None = None, total: int | None = None
	) -> int:
		if ticket_counts is not None:
			if types := self.ticket_types.get(zone):
				return sum(ticket_counts.get(ticket_type, 0) for ticket_type in types)
			return total if total is not None else sum(ticket_counts.values())
		filters = {"event": self.event, "docstatus": 1}
		if types := self.ticket_types.get(zone):
			filters["ticket_type"] = ["in", list(types)]
		return frappe.db.count("Event Ticket", filters)

	def checked_in_any_zone(self) -> int:
		return self._any_zone_count


ZONE_CHECKIN_COUNTS_SQL = """
	SELECT ci.zone, COUNT(DISTINCT ci.ticket)
	FROM `tabEvent Check In` ci
	INNER JOIN `tabEvent Ticket` t ON t.name = ci.ticket
	WHERE ci.event = %(event)s
		AND ci.docstatus = 1
		AND t.docstatus = 1
		AND (
			(%(has_once)s = 1 AND ci.zone IN %(once_zones)s)
			OR (%(has_daily)s = 1 AND ci.zone IN %(daily_zones)s AND ci.date = %(today)s)
		)
	GROUP BY ci.zone WITH ROLLUP
"""


def zone_checkin_counts(event: str, zones: list[frappe._dict]) -> tuple[dict[str, int], int]:
	"""Distinct checked-in ticket counts per enabled zone and across all enabled zones in one ROLLUP query."""
	if not zones:
		return {}, 0
	once_zones = [str(zone.name) for zone in zones if zone.repeat_rule == ONCE_PER_EVENT]
	daily_zones = [str(zone.name) for zone in zones if zone.repeat_rule != ONCE_PER_EVENT]
	rows = frappe.db.sql(
		ZONE_CHECKIN_COUNTS_SQL,
		{
			"event": event,
			"today": today(),
			"has_once": 1 if once_zones else 0,
			"once_zones": tuple(once_zones) or ("",),
			"has_daily": 1 if daily_zones else 0,
			"daily_zones": tuple(daily_zones) or ("",),
		},
	)
	counts: dict[str, int] = {}
	any_count = 0
	for zone, count in rows:
		if zone is None:
			any_count = count or 0
		else:
			counts[str(zone)] = count or 0
	return counts, any_count


def ticket_zone_arrivals(
	event: str, tickets: list[str], zones_by_name: dict[str, frappe._dict]
) -> defaultdict[str, dict[str, datetime]]:
	"""Check-in timestamps for only the current page's tickets across enabled zones."""
	checkin = frappe.qb.DocType("Event Check In")
	rows = (
		frappe.qb.from_(checkin)
		.select(checkin.zone, checkin.ticket, checkin.creation, checkin.date)
		.where(
			(checkin.event == event)
			& (checkin.docstatus == 1)
			& checkin.ticket.isin(tickets)
			& checkin.zone.isin(list(zones_by_name))
		)
	).run(as_dict=True)
	today_date = frappe.utils.getdate(today())
	arrivals = defaultdict(dict)
	for row in rows:
		zone_row = zones_by_name.get(str(row.zone))
		if not zone_row:
			continue
		if zone_row.repeat_rule == ONCE_PER_EVENT or frappe.utils.getdate(row.date) == today_date:
			arrivals[str(row.zone)][row.ticket] = row.creation
	return arrivals
