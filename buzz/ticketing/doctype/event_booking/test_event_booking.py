# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from buzz.api.booking.exceptions import HiddenTicketType
from buzz.tests.base_test_cases import BookingTestCase, CouponTestCase, attendee_rows
from buzz.tests.factories import (
	BuzzCouponCodeFactory,
	EventBookingFactory,
	EventTicketFactory,
	EventTicketTypeFactory,
)

UTM_PARAMETERS = {
	"utm_source": "facebook",
	"utm_medium": "social",
	"utm_campaign": "winter_promo",
	"utm_content": "banner_ad",
	"utm_term": "event tickets",
}


class TestTicketAvailability(BookingTestCase):
	def test_prevents_booking_if_tickets_unavailable(self):
		vip = EventTicketTypeFactory.create(event=self.event.name, max_tickets_available=2).name
		normal = self.free_ticket_type.name
		EventTicketFactory.create("submitted", event=self.event.name, ticket_type=vip)
		self.create_booking(vip, normal).submit()

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(vip, normal)

		frappe.db.set_value("Event Ticket Type", normal, "is_published", 0)
		frappe.clear_document_cache("Event Ticket Type", normal)
		with self.assertRaises(frappe.ValidationError):
			self.create_booking(normal)

	def test_late_payment_books_a_sold_out_ticket_type(self):
		paid = EventTicketTypeFactory.create("paid", event=self.event.name, max_tickets_available=1).name
		booking = self.create_booking(paid)
		EventTicketFactory.create("submitted", event=self.event.name, ticket_type=paid)

		with patch("buzz.ticketing.doctype.event_booking.event_booking.frappe.log_error") as log_error:
			booking.on_payment_authorized("Completed")

		self.assertEqual(booking.docstatus, 1)
		self.assertEqual(log_error.call_args.kwargs["reference_name"], booking.name)

	def test_late_payment_books_a_ticket_type_unpublished_meanwhile(self):
		paid = EventTicketTypeFactory.create("paid", event=self.event.name).name
		booking = self.create_booking(paid)
		frappe.db.set_value("Event Ticket Type", paid, "is_published", 0)
		frappe.clear_document_cache("Event Ticket Type", paid)

		booking.on_payment_authorized("Completed")

		self.assertEqual(booking.docstatus, 1)

	def test_refuses_booking_once_oversold_by_one(self):
		vip = EventTicketTypeFactory.create(event=self.event.name, max_tickets_available=1).name
		EventTicketFactory.create_list(2, "submitted", event=self.event.name, ticket_type=vip)

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(vip)

	def test_counts_tickets_with_a_locking_read(self):
		ticket_type = EventTicketTypeFactory.create(event=self.event.name, max_tickets_available=3)
		EventTicketFactory.create("submitted", event=self.event.name, ticket_type=ticket_type.name)

		self.assertEqual(ticket_type.get_remaining_tickets(for_update=True), 2)

	def create_booking(self, *ticket_types: str):
		attendees = [
			{"first_name": "John", "ticket_type": ticket_type, "email": "john@example.com"}
			for ticket_type in ticket_types
		]
		return EventBookingFactory.create(event=self.event.name, attendees=attendees)


class TestProcessBooking(BookingTestCase):
	def test_saves_utm_parameters(self):
		utm_parameters = [{"utm_name": name, "value": value} for name, value in UTM_PARAMETERS.items()]

		payload = self.process_as_booker(self.booking_request(utm_parameters=utm_parameters))

		booking = frappe.get_doc("Event Booking", payload.booking_name)
		self.assertEqual({row.utm_name: row.value for row in booking.utm_parameters}, UTM_PARAMETERS)

	def test_refuses_an_unpublished_event(self):
		self.set_event({"is_published": 0})

		with self.assertRaises(frappe.ValidationError) as raised:
			self.process_as_booker(self.booking_request())

		self.assertIn("Event is not live", str(raised.exception))


class TestZoomBackedCategoryBooking(BookingTestCase):
	def test_last_name_required_for_webinar_category(self):
		self.assertRaises(frappe.ValidationError, self.book_without_last_name, "Webinars")

	def test_last_name_required_for_zoom_meeting_category(self):
		self.assertRaises(frappe.ValidationError, self.book_without_last_name, "Zoom Meeting")

	def test_last_name_not_required_for_other_categories(self):
		payload = self.book_without_last_name(self.event.category)

		self.assertTrue(frappe.db.exists("Event Booking", payload.booking_name))

	def book_without_last_name(self, category: str):
		self.set_event({"category": category})
		return self.process_as_booker(self.booking_request())


class TestHiddenTicketBooking(CouponTestCase):
	def setUp(self):
		self.hidden = EventTicketTypeFactory.create(
			"is_hidden", event=self.event.name, prices=[{"currency": "INR", "price": 500}]
		)

	def create_access_code(self, **overrides):
		return BuzzCouponCodeFactory.create(
			"access_code",
			event=self.event.name,
			ticket_types=[{"ticket_type": self.hidden.name}],
			**overrides,
		)

	def book_hidden(self, access_code: str | None = None):
		return EventBookingFactory.create(
			event=self.event.name,
			access_code=access_code,
			attendees=attendee_rows(self.hidden.name, 1),
		)

	def test_hidden_ticket_type_is_refused_without_a_code(self):
		with self.assertRaises(HiddenTicketType):
			self.book_hidden()

	def test_hidden_ticket_type_is_refused_with_a_code_that_does_not_cover_it(self):
		other = EventTicketTypeFactory.create("is_hidden", event=self.event.name)
		code = BuzzCouponCodeFactory.create(
			"access_code", event=self.event.name, ticket_types=[{"ticket_type": other.name}]
		)

		with self.assertRaises(HiddenTicketType):
			self.book_hidden(code.name)

	def test_hidden_ticket_type_books_with_a_valid_code(self):
		code = self.create_access_code()

		booking = self.book_hidden(code.name)

		self.assertEqual(booking.access_code, code.name)
		self.assert_amounts(booking, net=500, discount=0, total=500)
		self.assertIsNone(booking.coupon_code)

	def test_access_code_with_a_discount_fills_the_coupon_code_too(self):
		code = self.create_access_code(discount_type="Percentage", discount_percentage=20)

		booking = self.book_hidden(code.name)

		self.assertEqual((booking.access_code, booking.coupon_code), (code.name, code.name))
		self.assert_amounts(booking, net=500, discount=100, total=400)

	def test_access_code_without_a_discount_keeps_the_automatic_offer(self):
		automatic = self.create_coupon("automatic")
		# Rollback is per class, so a live offer would discount later tests.
		self.addCleanup(frappe.db.set_value, "Buzz Coupon Code", automatic.name, "enabled", 0)
		code = self.create_access_code()

		booking = self.book_hidden(code.name)

		self.assertEqual((booking.access_code, booking.coupon_code), (code.name, automatic.name))
		self.assert_amounts(booking, net=500, discount=50, total=450)

	def test_usage_limit_of_one_blocks_the_second_booking(self):
		code = self.create_access_code(usage_limit=1)
		self.book_hidden(code.name).submit()

		with self.assertRaises(frappe.ValidationError):
			self.book_hidden(code.name)

	def test_expired_access_code_is_refused(self):
		code = self.create_access_code(expires_on=frappe.utils.add_days(frappe.utils.today(), -1))

		with self.assertRaises(frappe.ValidationError):
			self.book_hidden(code.name)

	def test_access_code_is_not_used_up_by_a_booking_without_its_hidden_tickets(self):
		code = self.create_access_code(usage_limit=1)

		self.create_booking(access_code=code.name).submit()

		self.assertEqual(self.book_hidden(code.name).access_code, code.name)
