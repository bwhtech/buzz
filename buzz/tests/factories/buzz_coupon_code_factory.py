from typing import Any

from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.ticketing.doctype.buzz_coupon_code.buzz_coupon_code import BuzzCouponCode


class BuzzCouponCodeFactory(BaseFactory[BuzzCouponCode]):
	"""A 10% discount on any event. `autoname` generates the code."""

	doctype = "Buzz Coupon Code"

	@property
	def default_attributes(self) -> dict[str, Any]:
		return {"coupon_type": "Discount", "discount_type": "Percentage", "discount_value": 10}

	@property
	def percentage(self) -> dict[str, Any]:
		return {"coupon_type": "Discount", "discount_type": "Percentage"}

	@property
	def flat(self) -> dict[str, Any]:
		return {"coupon_type": "Discount", "discount_type": "Flat Amount"}

	@property
	def free_tickets(self) -> dict[str, Any]:
		"""One free ticket. Pass `event` and its `ticket_type` together."""
		from buzz.tests.factories import BuzzEventFactory, EventTicketTypeFactory

		event = self.overrides.get("event") or BuzzEventFactory.create().name
		ticket_type = self.overrides.get("ticket_type") or EventTicketTypeFactory.create(event=event).name
		return {
			"coupon_type": "Free Tickets",
			"applies_to": "Event",
			"event": event,
			"ticket_type": ticket_type,
			"number_of_free_tickets": 1,
		}
