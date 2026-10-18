from typing import Any

import frappe
from frappe.utils import add_to_date, now_datetime
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.ticketing.doctype.ticket_hold.ticket_hold import HOLD_MINUTES, TicketHold


class TicketHoldFactory(BaseFactory[TicketHold]):
	"""A live hold of one ticket, held by another booking form."""

	doctype = "Ticket Hold"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import EventTicketTypeFactory

		ticket_type = self.overrides.get("ticket_type") or EventTicketTypeFactory.create().name
		return {
			"ticket_type": ticket_type,
			"event": self.overrides.get("event")
			or frappe.db.get_value("Event Ticket Type", ticket_type, "event"),
			"hold_token": frappe.generate_hash(length=32),
			"quantity": 1,
			"expires_at": add_to_date(now_datetime(), minutes=HOLD_MINUTES),
		}

	@property
	def expired(self) -> dict[str, Any]:
		return {"expires_at": add_to_date(now_datetime(), seconds=-1)}
