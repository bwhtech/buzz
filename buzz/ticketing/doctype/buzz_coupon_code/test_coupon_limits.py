import frappe
from frappe.utils import add_days, today

from buzz.tests.base_test_cases import CouponTestCase


class TestCouponExpiry(CouponTestCase):
	def test_usable_on_the_day_before(self):
		coupon = self.create_coupon(expires_on=add_days(today(), 1)).name

		self.assertEqual(self.create_booking(coupon).discount_amount, 50)

	def test_usable_on_the_expiry_day(self):
		coupon = self.create_coupon(expires_on=today()).name

		self.assertEqual(self.create_booking(coupon).discount_amount, 50)

	def test_refused_the_day_after(self):
		coupon = self.create_coupon(expires_on=add_days(today(), -1)).name

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(coupon)

	def test_submit_after_expiry_refused(self):
		coupon = self.create_coupon(expires_on=today()).name
		booking = self.create_booking(coupon)

		with self.freeze_time(add_days(today(), 1)), self.assertRaises(frappe.ValidationError):
			booking.submit()

	def test_disabled_coupon_refused(self):
		coupon = self.create_coupon(enabled=0).name

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(coupon)


class TestCouponUsageLimit(CouponTestCase):
	def test_refused_once_limit_is_reached(self):
		coupon = self.create_coupon(usage_limit=2).name
		self.create_booking(coupon).submit()
		self.create_booking(coupon).submit()

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(coupon)

	def test_drafts_and_cancelled_bookings_not_counted(self):
		coupon = self.create_coupon(usage_limit=1).name
		self.create_booking(coupon)
		cancelled = self.create_booking(coupon)
		cancelled.submit()
		cancelled.cancel()

		self.create_booking(coupon).submit()

	def test_zero_is_unlimited(self):
		coupon = self.create_coupon(usage_limit=0).name

		for _ in range(3):
			self.create_booking(coupon).submit()

	def test_limit_rechecked_on_submit(self):
		coupon = self.create_coupon(usage_limit=1).name
		first = self.create_booking(coupon)
		second = self.create_booking(coupon)
		first.submit()

		with self.assertRaises(frappe.ValidationError):
			second.submit()


class TestCouponOncePerBuyer(CouponTestCase):
	def test_same_email_in_different_case_refused(self):
		coupon = self.create_coupon(once_per_buyer=1).name
		self.create_booking(coupon, buyer_email="buyer@example.com").submit()

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(coupon, buyer_email="Buyer@Example.com")

	def test_another_email_allowed(self):
		coupon = self.create_coupon(once_per_buyer=1).name
		self.create_booking(coupon, buyer_email="buyer@example.com").submit()

		booking = self.create_booking(coupon, buyer_email="someone@example.com")

		self.assertEqual(booking.discount_amount, 50)

	def test_applies_to_automatic_coupons(self):
		coupon = self.create_coupon("automatic", once_per_buyer=1).name
		self.create_booking(buyer_email="auto@example.com").submit()

		booking = self.create_booking(buyer_email="auto@example.com")

		self.assertEqual((booking.coupon_code, booking.discount_amount), (None, 0))
		self.assertEqual(self.create_booking(buyer_email="new@example.com").coupon_code, coupon)

	def test_rechecked_on_submit(self):
		coupon = self.create_coupon(once_per_buyer=1).name
		first = self.create_booking(coupon, buyer_email="race@example.com")
		second = self.create_booking(coupon, buyer_email="race@example.com")
		first.submit()

		with self.assertRaises(frappe.ValidationError):
			second.submit()
