from typing import Any

import frappe
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.ticketing.doctype.event_ticket_category.event_ticket_category import EventTicketCategory


class EventTicketCategoryFactory(BaseFactory[EventTicketCategory]):
	doctype = "Event Ticket Category"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzEventFactory

		return {
			"event": self.overrides.get("event") or BuzzEventFactory.create().name,
			"title": f"Category {frappe.generate_hash(length=8)}",
		}
