from typing import Any

import frappe
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.ticketing.doctype.ticket_add_on.ticket_add_on import TicketAddon


class TicketAddOnFactory(BaseFactory[TicketAddon]):
	"""Free and enabled by default — `enabled` and `currency` come from the DocType."""

	doctype = "Ticket Add-on"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories.buzz_event_factory import BuzzEventFactory

		return {
			"event": self.overrides.get("event") or BuzzEventFactory.create().name,
			"title": f"Add-on {frappe.generate_hash(length=6)}",
		}

	@property
	def paid(self) -> dict[str, Any]:
		return {"price": 500}
