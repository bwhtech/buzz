from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.ticketing.doctype.attendee_ticket_add_on.attendee_ticket_add_on import AttendeeTicketAddon

_fake = Faker()


class AttendeeTicketAddOnFactory(BaseFactory[AttendeeTicketAddon]):
	"""An attendee's add-on selection with no values. Link it from a booking attendee's `add_ons`."""

	doctype = "Attendee Ticket Add-on"

	@property
	def default_attributes(self) -> dict[str, Any]:
		return {"attendee_name": _fake.name()}
