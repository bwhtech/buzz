from unittest.mock import patch

import frappe
from frappe.utils import add_days, add_to_date, now_datetime, today

from buzz.tests.base_test_cases import CouponTestCase, authorize_payment


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


class TestCouponSchedule(CouponTestCase):
	def test_refused_before_it_starts(self):
		coupon = self.create_coupon(starts_on=add_days(today(), 1)).name

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(coupon)

	def test_usable_on_the_start_day(self):
		coupon = self.create_coupon(starts_on=today()).name

		self.assertEqual(self.create_booking(coupon).discount_amount, 50)


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
		# Cancelling mails each attendee, and a test site configures no email account.
		with patch("frappe.sendmail"):
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


class TestCouponAfterPayment(CouponTestCase):
	"""The money is taken, so a coupon that went stale meanwhile must not fail the booking."""

	def setUp(self):
		super().setUp()
		# Confirming mails the tickets; without an email account that failure lands in log_error.
		self.enterContext(patch("frappe.sendmail"))

	def test_limit_reached_meanwhile_keeps_the_discount(self):
		coupon = self.create_coupon(usage_limit=1).name
		paid = self.create_booking(coupon)
		self.create_booking(coupon).submit()

		with patch("buzz.ticketing.doctype.event_booking.event_booking.frappe.log_error") as log_error:
			authorize_payment(paid)

		self.assert_confirmed_with_discount(paid, 50)
		self.assertEqual(log_error.call_args.kwargs["reference_name"], paid.name)

	def test_late_payment_beside_an_unpaid_reservation_is_not_logged(self):
		coupon = self.create_coupon(usage_limit=1).name
		late = self.create_booking(coupon, buyer_email="late@example.com")
		with self.freeze_time(add_to_date(now_datetime(), minutes=16), tick=True):
			self.create_booking(coupon, buyer_email="next@example.com")

			with patch("buzz.ticketing.doctype.event_booking.event_booking.frappe.log_error") as log_error:
				authorize_payment(late)

		self.assertFalse(log_error.called)

	def test_buyer_used_it_meanwhile_keeps_the_discount(self):
		coupon = self.create_coupon(once_per_buyer=1).name
		paid = self.create_booking(coupon, buyer_email="twice@example.com")
		self.create_booking(coupon, buyer_email="twice@example.com").submit()

		authorize_payment(paid)

		self.assert_confirmed_with_discount(paid, 50)

	def test_expired_meanwhile_keeps_the_discount(self):
		paid = self.create_booking(self.create_coupon(expires_on=today()).name)

		with self.freeze_time(add_days(today(), 1), tick=True):
			authorize_payment(paid)

		self.assert_confirmed_with_discount(paid, 50)

	def test_disabled_meanwhile_keeps_the_discount(self):
		coupon = self.create_coupon().name
		paid = self.create_booking(coupon)
		frappe.db.set_value("Buzz Coupon Code", coupon, "enabled", 0)

		authorize_payment(paid)

		self.assert_confirmed_with_discount(paid, 50)

	def test_automatic_coupon_added_meanwhile_is_not_applied(self):
		paid = self.create_booking()
		self.create_coupon("automatic")

		authorize_payment(paid)

		self.assert_confirmed_with_discount(paid, 0)
		self.assertIsNone(paid.coupon_code)

	def test_offline_approval_after_disable_keeps_the_discount(self):
		coupon = self.create_coupon().name
		offline = self.create_booking(coupon, payment_method="Offline")
		frappe.db.set_value("Buzz Coupon Code", coupon, "enabled", 0)

		offline.approve_booking()

		self.assert_confirmed_with_discount(offline, 50)

	def assert_confirmed_with_discount(self, booking, discount: int):
		self.assertEqual((booking.docstatus, booking.discount_amount), (1, discount))


class TestCouponReservations(CouponTestCase):
	"""A draft waiting for payment holds a use, so the last use can't be paid for twice."""

	def test_paying_draft_reserves_the_last_use(self):
		coupon = self.create_coupon(usage_limit=1).name
		self.create_booking(coupon, buyer_email="first@example.com")

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(coupon, buyer_email="second@example.com")

	def test_reservation_lapses_after_the_payment_window(self):
		coupon = self.create_coupon(usage_limit=1).name
		self.create_booking(coupon, buyer_email="first@example.com")

		with self.freeze_time(add_to_date(now_datetime(), minutes=16), tick=True):
			booking = self.create_booking(coupon, buyer_email="second@example.com")

		self.assertEqual(booking.discount_amount, 50)

	def test_own_draft_does_not_block_a_retry(self):
		coupon = self.create_coupon(usage_limit=1).name
		self.create_booking(coupon, buyer_email="retry@example.com")

		booking = self.create_booking(coupon, buyer_email="retry@example.com")

		self.assertEqual(booking.discount_amount, 50)

	def test_offline_draft_reserves_until_rejected(self):
		coupon = self.create_coupon(usage_limit=1).name
		offline = self.create_booking(coupon, buyer_email="first@example.com", payment_method="Offline")

		with self.freeze_time(add_to_date(now_datetime(), minutes=16), tick=True):
			with self.assertRaises(frappe.ValidationError):
				self.create_booking(coupon, buyer_email="second@example.com")
			offline.reject_booking()
			booking = self.create_booking(coupon, buyer_email="second@example.com")

		self.assertEqual(booking.discount_amount, 50)
