from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.booking import (
	get_booking_details,
	get_event_booking_data,
	process_booking,
	send_guest_booking_otp,
	validate_coupon,
)
from buzz.api.booking.exceptions import AddOnNotForEvent, InvalidAddOnValue, RegistrationsClosed
from buzz.api.booking.schemas import BookingRequest
from buzz.api.forms.test_forms import ensure_prompt_named_record
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user

BOOKER = "booking-owner@example.com"
OUTSIDER = "booking-outsider@example.com"
VALID_PHONE = "+91-9000090000"

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
		owner = create_user("booking-team-owner@example.com", "Booking")
		cls.team = create_owned_team(f"Booking Test Team {frappe.generate_hash(length=6)}", owner)
		cls.event = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": f"Booking Test Event {frappe.generate_hash(length=6)}",
				"team": cls.team,
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

	def enable_phone_otp(self):
		self.set_event({"allow_guest_booking": 1, "guest_verification_method": "Phone OTP"})

	def test_alphabetic_phone_is_refused(self):
		self.enable_phone_otp()
		with self.assertRaises(frappe.ValidationError):
			send_guest_booking_otp(self.event.name, "abcd")
		self.assertFalse(frappe.cache.get_value("guest_booking_otp:phone:abcd"))

	def test_phone_of_the_wrong_length_is_refused(self):
		self.enable_phone_otp()
		with self.assertRaises(frappe.ValidationError):
			send_guest_booking_otp(self.event.name, "+91-12345")
		self.assertFalse(frappe.cache.get_value("guest_booking_otp:phone:+91-12345"))

	def test_valid_phone_returns_the_code(self):
		self.enable_phone_otp()
		response = send_guest_booking_otp(self.event.name, VALID_PHONE)
		self.assertTrue(response["otp"])
		self.assertTrue(frappe.cache.get_value(f"guest_booking_otp:phone:{VALID_PHONE}"))


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

	def test_gateway_booking_is_not_acknowledged(self):
		"""The acknowledgement belongs to the offline path only: a gateway booking is
		still unpaid at this point and gets its confirmation after the payment lands."""
		request = self.make_paid_request()

		with (
			patch("buzz.api.booking.services.get_payment_link_for_booking", return_value="/pay"),
			patch("frappe.sendmail") as sendmail,
		):
			process_booking(request)

		sendmail.assert_not_called()

	def test_offline_booking_acknowledges_then_confirms(self):
		"""Offline is a two-stage conversation: an acknowledgement while the payment is
		unverified, the existing confirmation only once an approval submits the booking."""
		self.set_event({"send_ticket_email": 0})
		if not frappe.db.exists("User", BOOKER):
			frappe.get_doc(
				{"doctype": "User", "email": BOOKER, "first_name": "Booking", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Offline Payment Method",
				"event": self.event.name,
				"title": f"Bank Transfer {frappe.generate_hash(length=6)}",
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
		request = self.make_paid_request(is_offline=True)

		frappe.set_user(BOOKER)
		self.addCleanup(frappe.set_user, "Administrator")

		with patch("frappe.sendmail") as sendmail:
			booking_name = process_booking(request).booking_name

			sendmail.assert_called_once()
			self.assertEqual(sendmail.call_args[1]["template"], "offline_booking_acknowledgement")
			self.assertIn(BOOKER, sendmail.call_args[1]["recipients"])
			self.assertFalse(frappe.db.exists("Event Ticket", {"booking": booking_name}))

			frappe.set_user("Administrator")
			frappe.get_doc("Event Booking", booking_name).approve_booking()

			self.assertEqual(sendmail.call_args[1]["template"], "booking_confirmation")

		self.assertTrue(frappe.db.exists("Event Ticket", {"booking": booking_name}))


class TestBookingAddOnPricing(BookingTestCase):
	"""The add-on price is server-authoritative: it comes from the Ticket Add-on catalog,
	never from the booking payload. A guest who names their own price must be ignored."""

	ADD_ON_PRICE = 500

	def setUp(self):
		super().setUp()
		self.add_on = frappe.get_doc(
			{
				"doctype": "Ticket Add-on",
				"event": self.event.name,
				"title": f"Meal {frappe.generate_hash(length=6)}",
				"price": self.ADD_ON_PRICE,
				"enabled": 1,
			}
		).insert(ignore_permissions=True)

	def book_with_add_on(self, add_on_row):
		attendees = [
			{
				"first_name": "Booker",
				"email": "booker@example.com",
				"ticket_type": str(self.free_ticket_type.name),
				"add_ons": [add_on_row],
			}
		]
		# The paid path builds a payment link from a gateway that tests do not configure;
		# stub it so the booking is created and its stored amounts can be read back.
		with patch("buzz.api.booking.services.get_payment_link_for_booking", return_value="/pay"):
			process_booking(self.booking_request(attendees=attendees))
		return frappe.get_last_doc("Event Booking")

	def test_client_supplied_price_is_ignored(self):
		# The exploit payload: a Rs 500 add-on booked for Rs 1.
		booking = self.book_with_add_on({"add_on": self.add_on.name, "value": "Veg", "price": 1})
		self.assertEqual(booking.attendees[0].add_on_total, self.ADD_ON_PRICE)
		self.assertEqual(booking.total_amount, self.ADD_ON_PRICE)

	def test_price_is_charged_when_omitted(self):
		# The legitimate payload carries no price; the catalog price must still be charged.
		booking = self.book_with_add_on({"add_on": self.add_on.name, "value": "Veg"})
		self.assertEqual(booking.attendees[0].add_on_total, self.ADD_ON_PRICE)


class TestBookingSelectionValidation(BookingTestCase):
	"""Every selection in the payload must be a legitimate server-side choice for this
	event. A client cannot name a ticket type or add-on the event never offered."""

	def setUp(self):
		super().setUp()
		self.add_on = frappe.get_doc(
			{
				"doctype": "Ticket Add-on",
				"event": self.event.name,
				"title": f"Meal {frappe.generate_hash(length=6)}",
				"price": 500,
				"enabled": 1,
				"user_selects_option": 1,
				"options": "Vegetarian meal\nNon-veg",
			}
		).insert(ignore_permissions=True)

		foreign_owner = create_user("booking-foreign-owner@example.com", "Foreign")
		foreign_team = create_owned_team(f"Foreign Team {frappe.generate_hash(length=6)}", foreign_owner)
		self.foreign_event = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": f"Foreign Event {frappe.generate_hash(length=6)}",
				"team": foreign_team,
				"start_date": "2030-01-01",
				"end_date": "2030-01-01",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"medium": "Online",
				"category": self.event.category,
				"host": self.event.host,
				"is_published": 1,
			}
		).insert(ignore_permissions=True)

	def attendee(self, **overrides):
		row = {
			"first_name": "Booker",
			"email": "booker@example.com",
			"ticket_type": str(self.free_ticket_type.name),
		}
		row.update(overrides)
		return row

	def book(self, attendees):
		# These payloads are rejected in validate, before finalize reaches a payment gateway.
		process_booking(self.booking_request(attendees=attendees))

	def test_ticket_type_from_another_event_is_refused(self):
		foreign_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": self.foreign_event.name,
				"title": f"Foreign Ticket {frappe.generate_hash(length=6)}",
				"price": 0,
				"is_published": 1,
			}
		).insert(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError):
			self.book([self.attendee(ticket_type=str(foreign_ticket_type.name))])
		self.assertIn("not available for this event", frappe.local.message_log[-1]["message"])

	def test_add_on_from_another_event_is_refused(self):
		foreign_add_on = frappe.get_doc(
			{
				"doctype": "Ticket Add-on",
				"event": self.foreign_event.name,
				"title": f"Foreign Meal {frappe.generate_hash(length=6)}",
				"price": 500,
				"enabled": 1,
			}
		).insert(ignore_permissions=True)

		with self.assertRaises(AddOnNotForEvent):
			self.book([self.attendee(add_ons=[{"add_on": foreign_add_on.name, "value": True}])])

	def test_disabled_add_on_is_refused(self):
		frappe.db.set_value("Ticket Add-on", self.add_on.name, "enabled", 0)
		with self.assertRaises(AddOnNotForEvent):
			self.book([self.attendee(add_ons=[{"add_on": self.add_on.name, "value": "Vegetarian meal"}])])

	def test_invalid_add_on_value_is_refused(self):
		with self.assertRaises(InvalidAddOnValue):
			self.book([self.attendee(add_ons=[{"add_on": self.add_on.name, "value": "Gold"}])])

	def test_a_legitimate_selection_is_accepted(self):
		with patch("buzz.api.booking.services.get_payment_link_for_booking", return_value="/pay"):
			self.book([self.attendee(add_ons=[{"add_on": self.add_on.name, "value": "Vegetarian meal"}])])
		booking = frappe.get_last_doc("Event Booking")
		self.assertEqual(booking.attendees[0].add_on_total, 500)


class TestBookingPhoneCustomFields(BookingTestCase):
	def setUp(self):
		super().setUp()
		self.phone_field = frappe.get_doc(
			{
				"doctype": "Buzz Custom Field",
				"event": self.event.name,
				"label": "Contact Number",
				"fieldname": "contact_number",
				"fieldtype": "Phone",
				"applied_to": "Booking",
				"enabled": 1,
				"order": 1,
			}
		).insert(ignore_permissions=True)

	def test_invalid_booking_level_phone_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			process_booking(self.booking_request(booking_custom_fields={"contact_number": "+91-12345"}))

	def test_valid_booking_level_phone_is_stored(self):
		payload = process_booking(
			self.booking_request(booking_custom_fields={"contact_number": VALID_PHONE})
		).__json__()
		stored = frappe.db.get_value(
			"Additional Field",
			{"parent": payload["booking_name"], "fieldname": "contact_number"},
			"value",
		)
		self.assertEqual(stored, VALID_PHONE)

	def test_a_rejected_phone_does_not_burn_the_guest_otp(self):
		# The OTP lives in the cache, which no rollback restores, so phone validation has to
		# run before verify_guest_otp deletes it — otherwise one typo costs the guest a code.
		self.set_event({"allow_guest_booking": 1, "guest_verification_method": "Phone OTP"})
		otp = send_guest_booking_otp(self.event.name, VALID_PHONE)["otp"]
		cache_key = f"guest_booking_otp:phone:{VALID_PHONE}"
		self.addCleanup(frappe.cache.delete_value, cache_key)

		frappe.set_user("Guest")
		self.addCleanup(frappe.set_user, "Administrator")
		with self.assertRaises(frappe.ValidationError):
			process_booking(
				self.booking_request(
					guest_email="guest-phone-otp@example.com",
					guest_full_name="Guest Phone",
					guest_phone=VALID_PHONE,
					otp=otp,
					booking_custom_fields={"contact_number": "+91-12345"},
				)
			)

		self.assertTrue(frappe.cache.get_value(cache_key))

	def test_invalid_attendee_level_phone_is_still_refused(self):
		frappe.db.set_value("Buzz Custom Field", self.phone_field.name, "applied_to", "Ticket")
		attendees = [
			{
				"first_name": "Booker",
				"email": "booker@example.com",
				"ticket_type": str(self.free_ticket_type.name),
				"custom_fields": {"contact_number": "+91-12345"},
			}
		]
		with self.assertRaises(frappe.ValidationError):
			process_booking(self.booking_request(attendees=attendees))


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
