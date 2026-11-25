from typing import Any

from frappe.utils import now_datetime
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.hosted_payments.doctype.hosted_payment.hosted_payment import HostedPayment


class HostedPaymentFactory(BaseFactory[HostedPayment]):
	"""A hub payment for a connected site, with no gateway request behind it."""

	doctype = "Hosted Payment"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzTeamFactory

		return {
			"team": self.overrides.get("team") or BuzzTeamFactory.create_owned_by().name,
			"amount": 1000,
			"currency": "INR",
			"return_url": "https://pro.example.com/return",
			"webhook_url": "https://pro.example.com/webhook",
		}

	@property
	def paid(self) -> dict[str, Any]:
		return {"status": "Paid", "paid_on": now_datetime(), "payment_method": "upi"}
