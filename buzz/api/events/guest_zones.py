from collections import defaultdict
from datetime import datetime

import frappe
from frappe.utils import today

from buzz.api.events.exceptions import ZoneNotFound
from buzz.api.events.schemas import ZoneOption, ZoneStatus
from buzz.events.doctype.event_check_in_zone.event_check_in_zone import (
	ONCE_PER_EVENT,
	default_zone,
	enabled_zones,
)


class GuestZones:
	"""The event's enabled check-in zones, and who has checked in at each."""

	def __init__(self, event: str):
		self.event = event
		self.zones = enabled_zones(event)
		self.ticket_types = self.zone_ticket_types()
		self.arrivals = zone_arrivals(event)

	def zone_ticket_types(self) -> dict[str, set[str]]:
		rows = frappe.get_all(
			"Event Check-in Zone Ticket Type",
			filters={"parent": ["in", [zone.name for zone in self.zones] or [""]]},
			fields=["parent", "ticket_type"],
		)
		types = defaultdict(set)
		for row in rows:
			types[str(row.parent)].add(str(row.ticket_type))
		return types

	def allows(self, zone: str, ticket_type: str | None) -> bool:
		allowed = self.ticket_types.get(zone)
		return not allowed or str(ticket_type) in allowed

	def statuses(self, ticket: str, ticket_type: str | None) -> list[ZoneStatus]:
		return [
			ZoneStatus(
				name=zone.name,
				title=zone.title,
				allowed=self.allows(zone.name, ticket_type),
				checked_in_at=self.arrivals[zone.name].get(ticket),
			)
			for zone in self.zones
		]

	def options(self) -> list[ZoneOption]:
		return [
			ZoneOption(
				name=zone.name,
				title=zone.title,
				is_default=bool(zone.is_default),
				checked_in=len(self.arrivals[zone.name]),
				eligible=self.eligible(zone.name),
			)
			for zone in self.zones
		]

	def eligible(self, zone: str) -> int:
		filters = {"event": self.event, "docstatus": 1}
		if types := self.ticket_types.get(zone):
			filters["ticket_type"] = ["in", list(types)]
		return frappe.db.count("Event Ticket", filters)

	def checked_in_any_zone(self) -> int:
		return len({ticket for zone in self.zones for ticket in self.arrivals[zone.name]})


def zone_arrivals(event: str) -> defaultdict[str, dict[str, datetime]]:
	"""When each submitted ticket checked in, keyed by zone, then ticket.

	Today for a "Once per day" zone, at any time for a "Once per event" one.
	"""
	# Query builder: the team check in the caller is the authorization.
	checkin = frappe.qb.DocType("Event Check In")
	ticket = frappe.qb.DocType("Event Ticket")
	zone_table = frappe.qb.DocType("Event Check-in Zone")
	condition = (
		(checkin.event == event)
		& (checkin.docstatus == 1)
		& (ticket.docstatus == 1)
		& ((zone_table.repeat_rule == ONCE_PER_EVENT) | (checkin.date == today()))
	)
	rows = (
		frappe.qb.from_(checkin)
		.join(ticket)
		.on(ticket.name == checkin.ticket)
		.join(zone_table)
		.on(zone_table.name == checkin.zone)
		.select(checkin.zone, checkin.ticket, checkin.creation)
		.where(condition)
	).run(as_dict=True)
	arrivals = defaultdict(dict)
	for row in rows:
		arrivals[str(row.zone)][row.ticket] = row.creation
	return arrivals


def guest_list_zone(event: str, zone: str | None) -> str:
	name = frappe.db.get_value(
		"Event Check-in Zone", {"name": zone or default_zone(event), "event": event, "enabled": 1}
	)
	if not name:
		ZoneNotFound.throw()
	return str(name)
