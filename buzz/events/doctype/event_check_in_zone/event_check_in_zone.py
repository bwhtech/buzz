# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

DEFAULT_ZONE_TITLE = "Main Entrance"
ONCE_PER_EVENT = "Once per event"


class EventCheckinZone(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buzz.events.doctype.event_check_in_zone_ticket_type.event_check_in_zone_ticket_type import (
			EventCheckinZoneTicketType,
		)

		enabled: DF.Check
		event: DF.Link
		is_default: DF.Check
		repeat_rule: DF.Literal["Once per day", "Once per event"]
		ticket_types: DF.TableMultiSelect[EventCheckinZoneTicketType]
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		if not self.is_default:
			return
		if not self.enabled:
			frappe.throw(_("The default zone cannot be disabled."))
		if frappe.db.exists(
			"Event Check-in Zone", {"event": self.event, "is_default": 1, "name": ["!=", self.name]}
		):
			frappe.throw(_("This event already has a default zone."))

	def on_trash(self):
		if self.is_default:
			frappe.throw(_("The default zone cannot be deleted."))

	def allows(self, ticket_type: str | None) -> bool:
		return not self.ticket_types or ticket_type in {row.ticket_type for row in self.ticket_types}

	def existing_checkin(self, ticket: str, date: str) -> str | None:
		filters = {"ticket": ticket, "zone": self.name, "docstatus": 1}
		if self.repeat_rule != ONCE_PER_EVENT:
			filters["date"] = date
		return frappe.db.exists("Event Check In", filters)


def default_zone(event: str) -> str | None:
	return frappe.db.get_value("Event Check-in Zone", {"event": event, "is_default": 1})


def create_default_zone(event: str) -> None:
	frappe.get_doc(
		{"doctype": "Event Check-in Zone", "event": event, "title": DEFAULT_ZONE_TITLE, "is_default": 1}
	).insert(ignore_permissions=True)


def enabled_zones(event: str) -> list[frappe._dict]:
	"""The event's enabled zones, default first."""
	return frappe.get_all(
		"Event Check-in Zone",
		filters={"event": event, "enabled": 1},
		fields=["name", "title", "is_default", "repeat_rule"],
		order_by="is_default desc, creation asc",
	)
