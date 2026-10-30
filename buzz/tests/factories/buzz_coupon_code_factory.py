from typing import Any

import frappe
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.ticketing.doctype.buzz_coupon_code.buzz_coupon_code import BuzzCouponCode


class BuzzCouponCodeFactory(BaseFactory[BuzzCouponCode]):
	"""A 10% promo code on a fresh event."""

	doctype = "Buzz Coupon Code"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzEventFactory

		return {
			"event": self.overrides.get("event") or BuzzEventFactory.create().name,
			"coupon_type": "Promo Code",
			"code": f"SAVE{frappe.generate_hash(length=6).upper()}",
			"discount_type": "Percentage",
			"discount_percentage": 10,
		}

	@property
	def automatic(self) -> dict[str, Any]:
		return {"coupon_type": "Automatic", "code": f"Group discount {frappe.generate_hash(length=4)}"}

	@property
	def access_code(self) -> dict[str, Any]:
		"""Without a discount; pass `ticket_types` with the hidden types it unlocks."""
		return {
			"coupon_type": "Access Code",
			"code": f"VIP{frappe.generate_hash(length=6).upper()}",
			"discount_type": "None",
			"applies_to_all_ticket_types": 0,
		}

	@property
	def flat(self) -> dict[str, Any]:
		return {"discount_type": "Flat Amount", "discount_amounts": [{"currency": "INR", "price": 100}]}
