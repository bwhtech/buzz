from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.ticketing.doctype.event_ticket.event_ticket import EventTicket

_fake = Faker()


class EventTicketFactory(BaseFactory[EventTicket]):
	"""A draft ticket on a new free ticket type. The booking flow submits; use `submitted` for that."""

	doctype = "Event Ticket"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzEventFactory, EventTicketTypeFactory

		event = self.overrides.get("event") or BuzzEventFactory.create().name
		ticket_type = self.overrides.get("ticket_type") or EventTicketTypeFactory.create(event=event).name
		return {
			"event": event,
			"ticket_type": ticket_type,
			"first_name": _fake.first_name(),
			"attendee_email": _fake.email(),
		}

	@property
	def submitted(self) -> dict[str, Any]:
		return {"docstatus": 1}
