from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import EventTicketType

_fake = Faker()


class EventTicketTypeFactory(BaseFactory[EventTicketType]):
	"""Free and published by default. `currency` falls back to the field default (INR)."""

	doctype = "Event Ticket Type"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories.buzz_event_factory import BuzzEventFactory

		return {
			"event": self.overrides.get("event") or BuzzEventFactory.create().name,
			"title": f"Ticket {_fake.unique.word().capitalize()}",
			"price": 0,
			"is_published": 1,
		}

	@property
	def paid(self) -> dict[str, Any]:
		return {"price": 500}
