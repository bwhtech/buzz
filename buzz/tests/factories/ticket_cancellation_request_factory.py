from typing import Any

from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.ticketing.doctype.ticket_cancellation_request.ticket_cancellation_request import (
	TicketCancellationRequest,
)


class TicketCancellationRequestFactory(BaseFactory[TicketCancellationRequest]):
	"""In review, naming no tickets. Pass `tickets` rows or `cancel_full_booking` to pick the scope."""

	doctype = "Ticket Cancellation Request"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import EventBookingFactory

		return {"booking": self.overrides.get("booking") or EventBookingFactory.create().name}
