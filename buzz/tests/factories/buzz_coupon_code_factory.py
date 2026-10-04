from typing import Any

from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.ticketing.doctype.buzz_coupon_code.buzz_coupon_code import BuzzCouponCode


class BuzzCouponCodeFactory(BaseFactory[BuzzCouponCode]):
	"""A 10% discount on any event. `autoname` generates the code."""

	doctype = "Buzz Coupon Code"

	@property
	def default_attributes(self) -> dict[str, Any]:
		return {"coupon_type": "Discount", "discount_type": "Percentage", "discount_value": 10}
