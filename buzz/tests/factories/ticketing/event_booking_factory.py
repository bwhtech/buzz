from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.ticketing.doctype.event_booking.event_booking import EventBooking

_fake = Faker()

# Shared so bookings built as link targets do not hit the User creation throttle.
LINK_BOOKER = "factory-booker@example.com"


class EventBookingFactory(BaseFactory[EventBooking]):
	"""A draft booking: one attendee on a new free ticket type. `insert` sets `owner`, so set it after."""

	doctype = "Event Booking"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzEventFactory, UserFactory

		event = self.overrides.get("event") or BuzzEventFactory.create().name
		return {
			"event": event,
			"user": self.overrides.get("user") or UserFactory.create_once(LINK_BOOKER).name,
			"attendees": self.overrides.get("attendees") or [self.attendee(event)],
		}

	def attendee(self, event: str) -> dict[str, Any]:
		from buzz.tests.factories import EventTicketTypeFactory

		return {
			"ticket_type": EventTicketTypeFactory.create(event=event).name,
			"first_name": _fake.first_name(),
			"email": _fake.email(),
		}
