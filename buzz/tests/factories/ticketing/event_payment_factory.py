from typing import Any

import frappe
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.ticketing.doctype.event_payment.event_payment import EventPayment


class EventPaymentFactory(BaseFactory[EventPayment]):
	"""An unpaid payment. Pass `reference_doctype`, `reference_docname` and `payment_gateway`."""

	doctype = "Event Payment"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import UserFactory
		from buzz.tests.factories.ticketing.event_booking_factory import LINK_BOOKER

		return {"user": self.overrides.get("user") or UserFactory.create_once(LINK_BOOKER).name}

	@property
	def received(self) -> dict[str, Any]:
		# Webhooks find the payment by its id, so each one is unique.
		return {"payment_received": 1, "payment_id": f"pay_{frappe.generate_hash(length=10)}"}
