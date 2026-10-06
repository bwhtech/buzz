# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today

from buzz.api.booking import validate_coupon
from buzz.tests.factories import BuzzCouponCodeFactory, UserFactory
from buzz.ticketing.doctype.buzz_coupon_code.coupon_test_case import CouponTestCase


class TestCouponUsageLimits(CouponTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.booker = UserFactory.create_once("coupon-booker@example.com").name
		cls.other_booker = UserFactory.create_once("coupon-other-booker@example.com").name

	def test_discount_coupon_usage_limit_enforced(self):
		coupon = BuzzCouponCodeFactory.create("percentage", max_usage_count=2).name
		self.book(coupon).submit()
		self.book(coupon).submit()

		with self.assertRaises(frappe.ValidationError):
			self.book(coupon)

	def test_discount_coupon_unlimited_usage(self):
		coupon = BuzzCouponCodeFactory.create("percentage", max_usage_count=0)

		for _ in range(5):
			self.book(coupon.name).submit()

		self.assertEqual(coupon.times_used, 5)

	def test_inactive_coupon_rejected(self):
		coupon = BuzzCouponCodeFactory.create("percentage", is_active=0).name

		with self.assertRaises(frappe.ValidationError):
			self.book(coupon)

	def test_max_usage_per_user_enforced(self):
		coupon = BuzzCouponCodeFactory.create("percentage", max_usage_per_user=1).name
		self.book(coupon, user=self.booker).submit()

		with self.set_user(self.booker):
			response = check_coupon(coupon, self.event.name)

		self.assertFalse(response["valid"])
		self.assertIn("maximum usage limit", response["error"].lower())

	def test_per_user_limit_does_not_affect_other_users(self):
		coupon = BuzzCouponCodeFactory.create("percentage", max_usage_per_user=1).name
		self.book(coupon, user=self.booker).submit()

		with self.set_user(self.other_booker):
			self.assertTrue(check_coupon(coupon, self.event.name)["valid"])


class TestValidateCouponAPI(CouponTestCase):
	def test_validate_coupon_returns_discount_info(self):
		coupon = BuzzCouponCodeFactory.create("percentage", discount_value=25).name

		response = check_coupon(coupon, self.event.name)

		self.assertTrue(response["valid"])
		self.assertEqual(
			(response["coupon_type"], response["discount_type"], response["discount_value"]),
			("Discount", "Percentage", 25),
		)

	def test_validate_coupon_returns_max_and_min_values(self):
		coupon = BuzzCouponCodeFactory.create(
			"percentage", discount_value=30, maximum_discount_amount=500, minimum_order_value=200
		).name

		response = check_coupon(coupon, self.event.name)

		self.assertTrue(response["valid"])
		self.assertEqual((response["max_discount_amount"], response["min_order_value"]), (500, 200))

	def test_validate_coupon_returns_free_tickets_info(self):
		coupon = BuzzCouponCodeFactory.create(
			"free_tickets", event=self.event.name, ticket_type=self.ticket_type.name, number_of_free_tickets=3
		).name

		response = check_coupon(coupon, self.event.name)

		self.assertTrue(response["valid"])
		self.assertEqual((response["coupon_type"], response["remaining_tickets"]), ("Free Tickets", 3))

	def test_validate_coupon_invalid_code(self):
		response = check_coupon("INVALIDCODE", self.event.name)

		self.assertFalse(response["valid"])
		self.assertIn("error", response)

	def test_coupon_not_yet_active(self):
		coupon = BuzzCouponCodeFactory.create("percentage", valid_from=add_days(today(), 1)).name

		response = check_coupon(coupon, self.event.name)

		self.assertFalse(response["valid"])
		self.assertIn("not yet active", response["error"].lower())

	def test_expired_coupon_rejected(self):
		coupon = BuzzCouponCodeFactory.create("percentage", valid_till=add_days(today(), -1)).name

		response = check_coupon(coupon, self.event.name)

		self.assertFalse(response["valid"])
		self.assertIn("expired", response["error"].lower())

	def test_coupon_within_validity_period(self):
		coupon = BuzzCouponCodeFactory.create(
			"percentage", valid_from=add_days(today(), -1), valid_till=add_days(today(), 7)
		).name

		self.assertTrue(check_coupon(coupon, self.event.name)["valid"])


def check_coupon(coupon: str, event) -> dict:
	return validate_coupon(coupon, str(event)).__json__()
