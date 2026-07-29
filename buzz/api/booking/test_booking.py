import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.booking import (
	get_booking_details,
	get_event_booking_data,
	process_booking,
	send_guest_booking_otp,
	validate_coupon,
)
from buzz.api.booking.exceptions import RegistrationsClosed
from buzz.api.booking.schemas import BookingRequest
from buzz.api.forms.test_forms import ensure_prompt_named_record

BOOKER = "booking-owner@example.com"
OUTSIDER = "booking-outsider@example.com"

EVENT_DATA_FIELDS = {
	"registrations_closed",
	"event_details",
	"available_ticket_types",
	"available_add_ons",
	"tax_settings",
	"custom_fields",
	"payment_gateways",
	"offline_payment_enabled",
	"offline_methods",
}

GUEST_EVENT_DETAIL_FIELDS = {
	"name",
	"title",
	"route",
	"start_date",
	"end_date",
	"start_time",
	"end_time",
	"time_zone",
	"time_zone_label",
	"venue",
	"medium",
	"category",
	"banner_image",
	"short_description",
	"free_event",
	"send_ticket_email",
	"allow_guest_booking",
	"guest_verification_method",
	"default_ticket_type",
}

DETAILS_FIELDS = {
	"doc",
	"tickets",
	"event",
	"venue",
	"can_transfer_ticket",
	"can_change_add_ons",
	"can_request_cancellation",
	"cancellation_request",
	"cancellation_requested_tickets",
	"cancelled_tickets",
}


class BookingTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		category = ensure_prompt_named_record("Event Category", "Test Booking Category")
		host = ensure_prompt_named_record("Event Host", "Test Booking Host")
		cls.event = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": f"Booking Test Event {frappe.generate_hash(length=6)}",
				"start_date": "2030-01-01",
				"end_date": "2030-01-01",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"medium": "Online",
				"category": category,
				"host": host,
				"is_published": 1,
			}
		).insert(ignore_permissions=True)
		cls.event.reload()

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.clear_messages()
		self.addCleanup(frappe.clear_document_cache, "Buzz Event", self.event.name)
		self.set_event({"is_published": 1, "registrations_close_at": None, "allow_guest_booking": 0})
		self.free_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": self.event.name,
				"title": f"Booking Free {frappe.generate_hash(length=6)}",
				"price": 0,
				"is_published": 1,
			}
		).insert(ignore_permissions=True)

	def set_event(self, values):
		frappe.db.set_value("Buzz Event", self.event.name, values)
		frappe.clear_document_cache("Buzz Event", self.event.name)

	def booking_request(self, **overrides):
		values = {
			"attendees": [
				{
					"first_name": "Booker",
					"email": "booker@example.com",
					"ticket_type": str(self.free_ticket_type.name),
				}
			],
			"event": str(self.event.name),
		}
		values.update(overrides)
		return BookingRequest(**values)


class TestSendGuestBookingOtp(BookingTestCase):
	def test_disabled_guest_booking_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			send_guest_booking_otp(self.event.name, "someone@example.com")
		self.assertIn("Guest booking is not enabled", frappe.local.message_log[-1]["message"])

	def test_refused_without_a_verification_method(self):
		self.set_event({"allow_guest_booking": 1, "guest_verification_method": "None"})
		with self.assertRaises(frappe.ValidationError):
			send_guest_booking_otp(self.event.name, "someone@example.com")
		self.assertIn("OTP verification is not enabled", frappe.local.message_log[-1]["message"])

	def test_blank_identifier_is_refused(self):
		self.set_event({"allow_guest_booking": 1, "guest_verification_method": "Email OTP"})
		with self.assertRaises(frappe.ValidationError):
			send_guest_booking_otp(self.event.name, "   ")

	def test_returns_the_code_in_tests(self):
		self.set_event({"allow_guest_booking": 1, "guest_verification_method": "Email OTP"})
		response = send_guest_booking_otp(self.event.name, "someone@example.com")
		self.assertTrue(response["otp"])
		self.assertTrue(frappe.cache.get_value("guest_booking_otp:email:someone@example.com"))


class TestGetEventBookingData(BookingTestCase):
	def test_shape(self):
		response = get_event_booking_data(self.event.route)
		payload = response.__json__()
		self.assertEqual(set(payload), EVENT_DATA_FIELDS)
		self.assertFalse(payload["registrations_closed"])
		self.assertEqual(payload["event_details"].name, self.event.name)

	def test_guests_get_a_trimmed_event(self):
		frappe.set_user("Guest")
		payload = get_event_booking_data(self.event.route).__json__()
		self.assertEqual(set(payload["event_details"]), GUEST_EVENT_DETAIL_FIELDS)

	def test_registrations_closed_flag(self):
		self.set_event({"registrations_close_at": "2020-01-01 00:00:00"})
		self.assertTrue(get_event_booking_data(self.event.route).registrations_closed)

	def test_unpublished_event_is_not_found(self):
		self.set_event({"is_published": 0})
		with self.assertRaises(frappe.DoesNotExistError):
			get_event_booking_data(self.event.route)


class TestProcessBooking(BookingTestCase):
	def test_free_booking_redirects_to_success(self):
		payload = process_booking(self.booking_request()).__json__()
		self.assertEqual(set(payload), {"booking_name", "redirect_to"})
		self.assertEqual(frappe.db.get_value("Event Booking", payload["booking_name"], "docstatus"), 1)

	def test_unpublished_event_is_refused(self):
		self.set_event({"is_published": 0})
		with self.assertRaises(frappe.ValidationError):
			process_booking(self.booking_request())
		self.assertIn("Event is not live", frappe.local.message_log[-1]["message"])

	def test_closed_registrations_are_refused(self):
		self.set_event({"registrations_close_at": "2020-01-01 00:00:00"})
		with self.assertRaises(RegistrationsClosed):
			process_booking(self.booking_request())
		self.assertEqual(RegistrationsClosed.http_status_code, 409)
		self.assertEqual(frappe.local.message_log[-1]["title"], "Registrations Closed")

	def make_paid_request(self, **overrides):
		paid_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": self.event.name,
				"title": f"Booking Paid {frappe.generate_hash(length=6)}",
				"price": 100,
				"is_published": 1,
			}
		).insert(ignore_permissions=True)
		return self.booking_request(
			attendees=[
				{
					"first_name": "Booker",
					"email": "booker@example.com",
					"ticket_type": str(paid_ticket_type.name),
				}
			],
			**overrides,
		)

	def test_offline_booking_without_a_method_is_refused(self):
		# process_booking commits, so a sibling test's method row survives rollback;
		# pin the lookup to a name that cannot exist.
		with self.assertRaises(frappe.ValidationError):
			process_booking(self.make_paid_request(is_offline=True, offline_payment_method="no-such-method"))
		self.assertIn("Offline payment is not enabled", frappe.local.message_log[-1]["message"])

	def test_offline_booking_awaits_approval(self):
		frappe.get_doc(
			{
				"doctype": "Offline Payment Method",
				"event": self.event.name,
				"title": f"Bank Transfer {frappe.generate_hash(length=6)}",
				"enabled": 1,
			}
		).insert(ignore_permissions=True)

		payload = process_booking(self.make_paid_request(is_offline=True)).__json__()
		self.assertEqual(set(payload), {"booking_name", "offline_payment"})
		self.assertIs(payload["offline_payment"], True)
		booking = frappe.db.get_value(
			"Event Booking", payload["booking_name"], ["status", "payment_status"], as_dict=True
		)
		self.assertEqual(booking.status, "Approval Pending")
		self.assertEqual(booking.payment_status, "Verification Pending")


class TestGetBookingDetails(BookingTestCase):
	def setUp(self):
		super().setUp()
		for email, first_name in ((BOOKER, "Booking"), (OUTSIDER, "Outsider")):
			if not frappe.db.exists("User", email):
				frappe.get_doc(
					{"doctype": "User", "email": email, "first_name": first_name, "send_welcome_email": 0}
				).insert(ignore_permissions=True)

	def make_booking_for(self, user):
		frappe.set_user(user)
		try:
			return process_booking(self.booking_request()).booking_name
		finally:
			frappe.set_user("Administrator")

	def test_shape(self):
		booking_name = process_booking(self.booking_request()).booking_name
		payload = get_booking_details(booking_name).__json__()
		self.assertEqual(set(payload), DETAILS_FIELDS)
		self.assertEqual(payload["doc"].name, booking_name)
		self.assertIsNone(payload["venue"])
		self.assertIsInstance(payload["can_transfer_ticket"], bool)
		self.assertEqual(payload["cancellation_requested_tickets"], [])
		self.assertEqual(payload["cancelled_tickets"], [])

	def test_the_booker_reads_their_own_booking(self):
		booking_name = self.make_booking_for(BOOKER)
		frappe.set_user(BOOKER)

		self.assertEqual(get_booking_details(booking_name).doc.name, booking_name)

	def test_another_user_cannot_read_the_booking(self):
		booking_name = self.make_booking_for(BOOKER)
		frappe.set_user(OUTSIDER)

		with self.assertRaises(frappe.PermissionError):
			get_booking_details(booking_name)

	def test_a_privileged_user_may_read_any_booking(self):
		booking_name = self.make_booking_for(BOOKER)

		self.assertEqual(get_booking_details(booking_name).doc.name, booking_name)


class TestValidateCoupon(BookingTestCase):
	def test_unknown_coupon(self):
		payload = validate_coupon("NO-SUCH-COUPON", str(self.event.name)).__json__()
		self.assertEqual(payload, {"valid": False, "error": "Invalid coupon code"})

	def test_discount_coupon_shape(self):
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"code": f"BOOKING{frappe.generate_hash(length=6).upper()}",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 10,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

		payload = validate_coupon(coupon.name, str(self.event.name)).__json__()
		self.assertEqual(
			set(payload),
			{
				"valid",
				"coupon_type",
				"discount_type",
				"discount_value",
				"max_discount_amount",
				"min_order_value",
			},
		)
		self.assertTrue(payload["valid"])
		self.assertEqual(payload["max_discount_amount"], 0)
