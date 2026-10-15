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
		self.set_event(
			{
				"allow_guest_booking": 1,
				"guest_verification_method": "None",
				"prevent_duplicate_registrations": 0,
			}
		)
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

	def test_duplicate_guest_registrations_are_allowed_by_default(self):
		with self.set_user("Guest"):
			self.book_as_guest()
			payload = self.book_as_guest()

		self.assertTrue(frappe.db.exists("Event Booking", payload.booking_name))

	def test_duplicate_guest_registration_is_rejected_when_enabled(self):
		self.set_event({"prevent_duplicate_registrations": 1})
		with self.set_user("Guest"):
			self.book_as_guest()
			with self.assertRaises(frappe.ValidationError) as raised:
				self.book_as_guest(guest_email=self.email.upper(), attendee_email=f" {self.email.upper()} ")

		self.assertEqual(
			str(raised.exception), "This email address already has a registration for this event"
		)

	def test_cancelled_booking_does_not_block_a_new_registration(self):
		self.set_event({"prevent_duplicate_registrations": 1})
		with self.set_user("Guest"):
			payload = self.book_as_guest()
		frappe.get_doc("Event Booking", payload.booking_name).cancel()

		with self.set_user("Guest"):
			new_payload = self.book_as_guest()

		self.assertTrue(frappe.db.exists("Event Booking", new_payload.booking_name))

	def test_different_attendee_emails_can_register_for_the_same_event(self):
		self.set_event({"prevent_duplicate_registrations": 1})
		with self.set_user("Guest"):
			self.book_as_guest()
			payload = self.book_as_guest(attendee_email="other@example.com")

		self.assertTrue(frappe.db.exists("Event Booking", payload.booking_name))

	def test_same_email_can_register_for_a_different_event(self):
		self.set_event({"prevent_duplicate_registrations": 1})
		with self.set_user("Guest"):
			self.book_as_guest()
			other_event = self.create_other_event()
			payload = self.book_as_guest(event=other_event.name, ticket_type=self.other_ticket_type.name)

		self.assertTrue(frappe.db.exists("Event Booking", payload.booking_name))

	def test_duplicate_attendee_emails_in_one_request_are_rejected(self):
		self.set_event({"prevent_duplicate_registrations": 1})
		attendees = [
			{"first_name": "First", "email": self.email, "ticket_type": str(self.free_ticket_type.name)},
			{
				"first_name": "Second",
				"email": f" {self.email.upper()} ",
				"ticket_type": str(self.free_ticket_type.name),
			},
		]
		with self.set_user("Guest"), self.assertRaises(frappe.ValidationError) as raised:
			process_booking(self.booking_request(attendees=attendees, guest_email=self.email))

		self.assertEqual(
			str(raised.exception), "This email address already has a registration for this event"
		)
		self.assertFalse(frappe.db.exists("User", self.email))

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
		event = overrides.pop("event", self.event.name)
		attendee_email = overrides.pop("attendee_email", self.email)
		ticket_type = overrides.pop("ticket_type", self.free_ticket_type.name)
		attendees = [
			{
				"ticket_type": str(ticket_type),
				"first_name": "Test",
				"last_name": "Guest",
				"email": attendee_email,
			}
		]
		values = {"guest_email": self.email, "guest_full_name": "Test Guest", **overrides}
		return process_booking(self.booking_request(event=str(event), attendees=attendees, **values))

	def create_other_event(self):
		from buzz.tests.factories import BuzzEventFactory, EventTicketTypeFactory

		event = BuzzEventFactory.create(
			allow_guest_booking=1,
			guest_verification_method="None",
			prevent_duplicate_registrations=1,
		)
		self.addCleanup(frappe.clear_document_cache, "Buzz Event", event.name)
		self.other_ticket_type = EventTicketTypeFactory.create(event=event.name)
		return event

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
