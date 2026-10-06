# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

from base64 import b32encode

import frappe
import pyotp

from buzz.api.booking import process_booking
from buzz.tests.base_test_cases import BookingTestCase

OTP_SECRET = b32encode(b"TESTSECRET").decode("utf-8")
WRONG_OTP = "000000"


class TestGuestBooking(BookingTestCase):
	def setUp(self):
		super().setUp()
		self.set_event({"allow_guest_booking": 1, "guest_verification_method": "None"})
		self.email = f"testguest-{frappe.generate_hash(length=8)}@example.com"
		# process_booking commits, so the guest's User outlives the rollback.
		self.addCleanup(self.delete_guest_user)

	def test_guest_booking_without_otp_creates_the_booking_and_user(self):
		with self.set_user("Guest"):
			payload = self.book_as_guest()

		self.assertTrue(frappe.db.exists("Event Booking", payload.booking_name))
		self.assertIn("Buzz User", frappe.get_roles(self.email))

	def test_guest_booking_with_otp_clears_the_code(self):
		self.enable_email_otp()
		self.store_otp()

		with self.set_user("Guest"):
			payload = self.book_as_guest(otp=pyotp.HOTP(OTP_SECRET).at(0))

		self.assertTrue(frappe.db.exists("Event Booking", payload.booking_name))
		self.assertIsNone(frappe.cache.get_value(self.otp_cache_key()))

	def test_guest_booking_rejected_when_disabled(self):
		self.set_event({"allow_guest_booking": 0})

		with self.set_user("Guest"), self.assertRaises(frappe.AuthenticationError):
			self.book_as_guest()

	def test_invalid_otp_rejected(self):
		self.enable_email_otp()
		self.store_otp()

		with self.set_user("Guest"), self.assertRaises(frappe.ValidationError):
			self.book_as_guest(otp=WRONG_OTP)

	def test_guest_booking_requires_email(self):
		with self.set_user("Guest"), self.assertRaises(frappe.ValidationError):
			self.book_as_guest(guest_email="")

	def test_brute_force_lockout(self):
		# LoginAttemptTracker(max_consecutive_login_attempts=5) compares with `>`,
		# so the lockout starts after the sixth failure.
		self.enable_email_otp()

		with self.set_user("Guest"):
			for _ in range(6):
				self.store_otp()
				with self.assertRaises(frappe.ValidationError):
					self.book_as_guest(otp=WRONG_OTP)

			self.store_otp()
			with self.assertRaises(frappe.ValidationError) as raised:
				self.book_as_guest(otp=WRONG_OTP)

		self.assertIn("Too many failed attempts", str(raised.exception))

	def book_as_guest(self, **overrides):
		attendees = [
			{
				"ticket_type": str(self.free_ticket_type.name),
				"first_name": "Test",
				"last_name": "Guest",
				"email": self.email,
			}
		]
		values = {"guest_email": self.email, "guest_full_name": "Test Guest", **overrides}
		return process_booking(self.booking_request(attendees=attendees, **values))

	def enable_email_otp(self):
		self.set_event({"guest_verification_method": "Email OTP"})

	def store_otp(self):
		"""What `send_guest_booking_otp` leaves in the cache."""
		frappe.cache.set_value(self.otp_cache_key(), OTP_SECRET, expires_in_sec=600)
		self.addCleanup(frappe.cache.delete_value, self.otp_cache_key())

	def otp_cache_key(self) -> str:
		return f"guest_booking_otp:email:{self.email}"

	def delete_guest_user(self):
		if frappe.db.exists("User", self.email):
			frappe.delete_doc("User", self.email, force=True, ignore_permissions=True)
