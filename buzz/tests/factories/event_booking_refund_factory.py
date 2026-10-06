from typing import Any

from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.ticketing.doctype.event_booking_refund.event_booking_refund import EventBookingRefund


class EventBookingRefundFactory(BaseFactory[EventBookingRefund]):
	"""An initiated refund. Pass `amount`; a refund of the booking total counts as a full refund."""

	doctype = "Event Booking Refund"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import EventBookingFactory

		return {
			"booking": self.overrides.get("booking") or EventBookingFactory.create().name,
			"status": "Initiated",
		}
