import frappe

from buzz.tests.base_test_cases import CouponTestCase
from buzz.tests.factories import BuzzCouponCodeFactory


class TestDiscountCoupon(CouponTestCase):
	def test_percentage_discount_applies_correctly(self):
		coupon = BuzzCouponCodeFactory.create("percentage", discount_value=20).name

		booking = self.create_booking(coupon, count=2)

		self.assert_amounts(booking, net=1000, discount=200, total=800)

	def test_flat_discount_applies_correctly(self):
		coupon = BuzzCouponCodeFactory.create("flat", discount_value=300).name

		self.assert_amounts(self.create_booking(coupon), net=500, discount=300, total=200)

	def test_flat_discount_does_not_exceed_total(self):
		coupon = BuzzCouponCodeFactory.create("flat", discount_value=1000).name

		self.assert_amounts(self.create_booking(coupon), net=500, discount=500, total=0)

	def test_percentage_discount_capped_at_max(self):
		coupon = BuzzCouponCodeFactory.create("percentage", discount_value=50, maximum_discount_amount=500)

		booking = self.create_booking(coupon.name, count=4)

		self.assert_amounts(booking, net=2000, discount=500, total=1500)

	def test_min_order_value_enforced(self):
		coupon = BuzzCouponCodeFactory.create("percentage", discount_value=20, minimum_order_value=1000)

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(coupon.name)

	def test_percentage_with_cap_and_min_order(self):
		coupon = BuzzCouponCodeFactory.create(
			"percentage", discount_value=50, maximum_discount_amount=300, minimum_order_value=500
		).name

		self.assert_amounts(self.create_booking(coupon, count=1), net=500, discount=250, total=250)
		self.assert_amounts(self.create_booking(coupon, count=2), net=1000, discount=300, total=700)

	def test_percentage_discount_cannot_exceed_100(self):
		with self.assertRaises(frappe.ValidationError):
			BuzzCouponCodeFactory.create("percentage", discount_value=150)

	def test_coupon_tracked_in_booking(self):
		code = f"TRACK{frappe.generate_hash(length=6).upper()}"
		BuzzCouponCodeFactory.create("percentage", code=code)

		self.assertEqual(self.create_booking(code).coupon_code, code)
