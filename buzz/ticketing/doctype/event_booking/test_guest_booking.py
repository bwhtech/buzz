# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import uuid
from base64 import b32encode

import frappe
import pyotp
from frappe.tests import IntegrationTestCase

from buzz.api.booking import process_booking


class TestGuestBooking(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		self.event_name = str(self.test_event.name)
		self.original_allow_guest = self.test_event.allow_guest_booking
		self.original_verification = self.test_event.guest_verification_method
		self.test_event.allow_guest_booking = True
		self.test_event.guest_verification_method = "None"
		self.test_event.is_published = True
		self.test_event.save()
		self.ticket_type = str(self._get_or_create_free_ticket_type())

	def tearDown(self):
		frappe.set_user("Administrator")
		self.test_event.reload()
		self.test_event.allow_guest_booking = self.original_allow_guest
		self.test_event.guest_verification_method = self.original_verification
		self.test_event.is_published = False
		self.test_event.save()

	# --- helpers ---

	def _generate_test_email(self):
		return f"testguest-{uuid.uuid4().hex[:8]}@example.com"

	def _cleanup_test_user(self, email):
		frappe.set_user("Administrator")
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True)

	def _get_or_create_free_ticket_type(self):
		existing = frappe.db.get_value(
			"Event Ticket Type",
			{"event": self.test_event.name, "price": 0},
			"name",
		)
		if existing:
			return existing
		return (
			frappe.get_doc(
				{
					"doctype": "Event Ticket Type",
					"event": self.test_event.name,
					"title": "Free (Test)",
					"price": 0,
				}
			)
			.insert()
			.name
		)

	def _make_attendees(self, email):
		return [{"ticket_type": self.ticket_type, "first_name": "Test", "last_name": "Guest", "email": email}]

	# --- tests ---

	def test_guest_booking_without_otp(self):
		"""Full happy path: guest books with verification='None', booking + user created."""
		email = self._generate_test_email()
		try:
			frappe.set_user("Guest")
			result = process_booking(
				attendees=self._make_attendees(email),
				event=self.event_name,
				guest_email=email,
				guest_full_name="Test Guest",
			)
			self.assertIn("booking_name", result)
			self.assertTrue(frappe.db.exists("Event Booking", result["booking_name"]))
			self.assertTrue(frappe.db.exists("User", email))
			self.assertIn("Buzz User", frappe.get_roles(email))
		finally:
			self._cleanup_test_user(email)

	def test_guest_booking_with_otp(self):
		"""OTP happy path: cache OTP, pass it in, booking succeeds, OTP cache cleared."""
		email = self._generate_test_email()
		self.test_event.guest_verification_method = "Email OTP"
		self.test_event.save()
		try:
			# Simulate OTP generation (same as send_guest_booking_otp)
			otp_secret = b32encode(b"TESTSECRET").decode("utf-8")
			otp_code = pyotp.HOTP(otp_secret).at(0)
			frappe.cache.set_value(
				f"guest_booking_otp:email:{email.lower().strip()}", otp_secret, expires_in_sec=600
			)

			frappe.set_user("Guest")
			result = process_booking(
				attendees=self._make_attendees(email),
				event=self.event_name,
				guest_email=email,
				guest_full_name="Test Guest",
				otp=str(otp_code),
			)
			self.assertIn("booking_name", result)
			# OTP cache should be cleared after successful verification
			self.assertIsNone(frappe.cache.get_value(f"guest_booking_otp:email:{email.lower().strip()}"))
		finally:
			self._cleanup_test_user(email)

	def test_guest_booking_rejected_when_disabled(self):
		"""Security gate: allow_guest_booking=False raises AuthenticationError."""
		self.test_event.allow_guest_booking = False
		self.test_event.save()

		frappe.set_user("Guest")
		with self.assertRaises(frappe.AuthenticationError):
			process_booking(
				attendees=self._make_attendees("nobody@example.com"),
				event=self.event_name,
				guest_email="nobody@example.com",
				guest_full_name="Nobody",
			)

	def test_invalid_otp_rejected(self):
		"""Wrong OTP code raises ValidationError."""
		email = self._generate_test_email()
		self.test_event.guest_verification_method = "Email OTP"
		self.test_event.save()

		otp_secret = b32encode(b"TESTSECRET").decode("utf-8")
		frappe.cache.set_value(
			f"guest_booking_otp:email:{email.lower().strip()}", otp_secret, expires_in_sec=600
		)

		frappe.set_user("Guest")
		with self.assertRaises(frappe.ValidationError):
			process_booking(
				attendees=self._make_attendees(email),
				event=self.event_name,
				guest_email=email,
				guest_full_name="Test Guest",
				otp="000000",
			)

	def test_guest_booking_requires_email(self):
		"""Missing email raises ValidationError."""
		frappe.set_user("Guest")
		with self.assertRaises(frappe.ValidationError):
			process_booking(
				attendees=[
					{
						"ticket_type": self.ticket_type,
						"first_name": "Test",
						"last_name": "Guest",
						"email": "t@e.com",
					}
				],
				event=self.event_name,
				guest_email="",
				guest_full_name="Test Guest",
			)

	def test_brute_force_lockout(self):
		"""Repeated wrong OTPs locks out subsequent attempts.

		LoginAttemptTracker(max_consecutive_login_attempts=5) uses strict >
		comparison, so lockout triggers after count exceeds the threshold.
		"""
		email = self._generate_test_email()
		self.test_event.guest_verification_method = "Email OTP"
		self.test_event.save()

		otp_secret = b32encode(b"TESTSECRET").decode("utf-8")
		cache_key = f"guest_booking_otp:email:{email.lower().strip()}"

		frappe.set_user("Guest")

		# Exhaust allowed attempts (Frappe's tracker uses > comparison,
		# so we need max_consecutive_login_attempts + 1 failures to trigger lockout)
		for _ in range(6):
			frappe.cache.set_value(cache_key, otp_secret, expires_in_sec=600)
			with self.assertRaises(frappe.ValidationError):
				process_booking(
					attendees=self._make_attendees(email),
					event=self.event_name,
					guest_email=email,
					guest_full_name="Test Guest",
					otp="000000",
				)

		# Next attempt should hit "Too many failed attempts"
		frappe.cache.set_value(cache_key, otp_secret, expires_in_sec=600)
		with self.assertRaises(frappe.ValidationError) as ctx:
			process_booking(
				attendees=self._make_attendees(email),
				event=self.event_name,
				guest_email=email,
				guest_full_name="Test Guest",
				otp="000000",
			)
		self.assertIn("Too many failed attempts", str(ctx.exception))
