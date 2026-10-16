# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe

from buzz.api.booking import process_booking
from buzz.tests.base_test_cases import BookingTestCase
from buzz.tests.factories import EventBookingFactory, EventTicketFactory, EventTicketTypeFactory

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

		booking.on_payment_authorized("Completed")

		self.assertEqual(booking.docstatus, 1)
		self.assertTrue(frappe.db.exists("Error Log", {"reference_name": booking.name}))

	def test_late_payment_books_a_ticket_type_unpublished_meanwhile(self):
		paid = EventTicketTypeFactory.create("paid", event=self.event.name).name
		booking = self.create_booking(paid)
		frappe.db.set_value("Event Ticket Type", paid, "is_published", 0)
		frappe.clear_document_cache("Event Ticket Type", paid)

		booking.on_payment_authorized("Completed")

		self.assertEqual(booking.docstatus, 1)

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

		payload = process_booking(self.booking_request(utm_parameters=utm_parameters))

		booking = frappe.get_doc("Event Booking", payload.booking_name)
		self.assertEqual({row.utm_name: row.value for row in booking.utm_parameters}, UTM_PARAMETERS)

	def test_refuses_an_unpublished_event(self):
		self.set_event({"is_published": 0})

		with self.assertRaises(frappe.ValidationError) as raised:
			process_booking(self.booking_request())

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
		return process_booking(self.booking_request())
