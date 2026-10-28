from types import SimpleNamespace
from unittest.mock import patch

import frappe
from pydantic import ValidationError

from buzz.api.booking import process_booking, send_guest_booking_otp
from buzz.api.booking.schemas import MAX_ATTENDEES_PER_BOOKING
from buzz.tests.base_test_cases import BookingTestCase


class RateLimitedTestCase(BookingTestCase):
	def setUp(self):
		super().setUp()
		self.enterContext(patch.object(frappe.local, "request", SimpleNamespace(method="POST"), create=True))
		self.enterContext(patch.object(frappe.local, "request_ip", frappe.generate_hash(length=12), create=True))


class TestProcessBookingLimits(RateLimitedTestCase):
	def test_guest_is_rate_limited(self):
		request = self.booking_request()
		with patch("buzz.api.booking.BookingService.process"), self.set_user("Guest"):
			for _attempt in range(20):
				process_booking(request)
			with self.assertRaises(frappe.RateLimitExceededError):
				process_booking(request)

	def test_attendees_per_booking_are_capped(self):
		attendee = self.booking_request().attendees[0]
		with self.assertRaises(ValidationError):
			self.booking_request(attendees=[attendee] * (MAX_ATTENDEES_PER_BOOKING + 1))


class TestSendGuestBookingOtpLimits(RateLimitedTestCase):
	def setUp(self):
		super().setUp()
		self.set_event({"allow_guest_booking": 1, "guest_verification_method": "Email OTP"})

	def send(self, identifier):
		frappe.form_dict["identifier"] = identifier
		return send_guest_booking_otp(self.event.name, identifier)

	def test_case_and_whitespace_variants_share_one_quota(self):
		variants = ["a@example.com", "A@example.com", " a@example.com", "a@EXAMPLE.com ", "A@Example.com"]
		for variant in variants:
			self.send(variant)
		with self.assertRaises(frappe.RateLimitExceededError):
			self.send(" A@example.COM")

	def test_one_network_is_capped_across_identifiers(self):
		for index in range(20):
			self.send(f"person{index}@example.com")
		with self.assertRaises(frappe.RateLimitExceededError):
			self.send("another@example.com")
