# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]

TEST_ADD_ON_PRICE = 100
TEST_VIP_TICKET_TYPE_PRICE = 500


class IntegrationTestEventBooking(IntegrationTestCase):
	"""
	Integration tests for EventBooking.
	Use this class for testing interactions between multiple components.
	"""

	def test_total_calculation_without_taxes(self):
		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})

		# Disable tax at event level
		test_event.apply_tax = False
		test_event.save()

		test_ticket_add_on = frappe.get_doc(
			{
				"doctype": "Ticket Add-on",
				"event": test_event.name,
				"title": "T-Shirt",
				"price": TEST_ADD_ON_PRICE,
			}
		).insert()

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "VIP",
				"price": TEST_VIP_TICKET_TYPE_PRICE,
			}
		).insert()

		test_booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": test_event.name,
				"user": "Administrator",
				"attendees": [
					{"ticket_type": test_ticket_type.name, "first_name": "John", "email": "john@email.com"},
					{"ticket_type": test_ticket_type.name, "first_name": "Jenny", "email": "jenny@email.com"},
				],
			}
		).insert()

		# without add ons
		self.assertEqual(test_booking.total_amount, 1000)

		test_attendee_add_on = frappe.get_doc(
			{
				"doctype": "Attendee Ticket Add-on",
				"add_ons": [{"add_on": test_ticket_add_on.name, "value": "XL"}],
			}
		).insert()

		test_booking.attendees[0].add_ons = test_attendee_add_on.name
		test_booking.save()

		# with one add-on
		self.assertEqual(test_booking.attendees[0].number_of_add_ons, 1)
		self.assertEqual(test_booking.attendees[0].add_on_total, TEST_ADD_ON_PRICE)
		self.assertEqual(test_booking.net_amount, 1100)
		self.assertEqual(test_booking.total_amount, 1100)

	def test_total_calculation_with_taxes(self):
		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})

		# Enable tax at event level (exclusive)
		test_event.apply_tax = True
		test_event.tax_inclusive = False
		test_event.tax_label = "GST"
		test_event.tax_percentage = 18
		test_event.save()

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "VIP",
				"price": TEST_VIP_TICKET_TYPE_PRICE,
			}
		).insert()

		test_booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": test_event.name,
				"user": "Administrator",
				"attendees": [
					{"ticket_type": test_ticket_type.name, "first_name": "John", "email": "john@email.com"},
					{"ticket_type": test_ticket_type.name, "first_name": "Jenny", "email": "jenny@email.com"},
				],
			}
		).insert()

		self.assertEqual(test_booking.net_amount, 1000)
		self.assertEqual(test_booking.tax_label, "GST")
		self.assertEqual(test_booking.tax_percentage, 18)
		self.assertEqual(test_booking.tax_amount, 180)
		self.assertEqual(test_booking.total_amount, 1180)

	def test_total_calculation_with_custom_tax_label(self):
		"""Test that custom tax labels (e.g., VAT) work correctly."""
		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})

		# Enable tax with custom VAT label (exclusive)
		test_event.apply_tax = True
		test_event.tax_inclusive = False
		test_event.tax_label = "VAT"
		test_event.tax_percentage = 20
		test_event.save()

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "Standard",
				"price": 100,
			}
		).insert()

		test_booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": test_event.name,
				"user": "Administrator",
				"attendees": [
					{"ticket_type": test_ticket_type.name, "first_name": "John", "email": "john@email.com"},
				],
			}
		).insert()

		self.assertEqual(test_booking.tax_label, "VAT")
		self.assertEqual(test_booking.tax_percentage, 20)
		self.assertEqual(test_booking.tax_amount, 20)
		self.assertEqual(test_booking.total_amount, 120)

	def test_tax_inclusive_calculation(self):
		"""Test that tax-inclusive prices back-calculate tax without increasing total."""
		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})

		# Enable tax-inclusive pricing
		test_event.apply_tax = True
		test_event.tax_inclusive = True
		test_event.tax_label = "GST"
		test_event.tax_percentage = 18
		test_event.save()

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "VIP",
				"price": TEST_VIP_TICKET_TYPE_PRICE,
			}
		).insert()

		test_booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": test_event.name,
				"user": "Administrator",
				"attendees": [
					{"ticket_type": test_ticket_type.name, "first_name": "John", "email": "john@email.com"},
					{"ticket_type": test_ticket_type.name, "first_name": "Jenny", "email": "jenny@email.com"},
				],
			}
		).insert()

		# net_amount = 2 * 500 = 1000
		self.assertEqual(test_booking.net_amount, 1000)
		self.assertEqual(test_booking.tax_label, "GST")
		self.assertEqual(test_booking.tax_percentage, 18)
		# tax_amount = 1000 * 18 / 118 = 152.54 (rounded to 2 decimals)
		self.assertAlmostEqual(test_booking.tax_amount, round(1000 * 18 / 118, 2), places=2)
		# total stays the same — tax is included in the price
		self.assertEqual(test_booking.total_amount, 1000)

	def test_tax_inclusive_with_single_ticket(self):
		"""Test tax-inclusive with a single ticket at a round price."""
		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})

		test_event.apply_tax = True
		test_event.tax_inclusive = True
		test_event.tax_label = "VAT"
		test_event.tax_percentage = 20
		test_event.save()

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "Standard",
				"price": 120,
			}
		).insert()

		test_booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": test_event.name,
				"user": "Administrator",
				"attendees": [
					{"ticket_type": test_ticket_type.name, "first_name": "John", "email": "john@email.com"},
				],
			}
		).insert()

		# Price is 120 inclusive of 20% VAT
		# tax_amount = 120 * 20 / 120 = 20
		self.assertEqual(test_booking.net_amount, 120)
		self.assertEqual(test_booking.tax_amount, 20)
		self.assertEqual(test_booking.total_amount, 120)

	def test_tax_exclusive_still_works(self):
		"""Ensure that when tax_inclusive is False, tax is still added on top."""
		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})

		test_event.apply_tax = True
		test_event.tax_inclusive = False
		test_event.tax_label = "GST"
		test_event.tax_percentage = 18
		test_event.save()

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "VIP",
				"price": TEST_VIP_TICKET_TYPE_PRICE,
			}
		).insert()

		test_booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": test_event.name,
				"user": "Administrator",
				"attendees": [
					{"ticket_type": test_ticket_type.name, "first_name": "John", "email": "john@email.com"},
					{"ticket_type": test_ticket_type.name, "first_name": "Jenny", "email": "jenny@email.com"},
				],
			}
		).insert()

		# Exclusive: tax added on top
		self.assertEqual(test_booking.net_amount, 1000)
		self.assertEqual(test_booking.tax_amount, 180)
		self.assertEqual(test_booking.total_amount, 1180)

	def test_prevents_booking_if_tickets_unavailable(self):
		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		test_vip_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "VIP",
				"price": 500,
				"is_published": True,
				"max_tickets_available": 2,
			}
		).insert()

		test_normal_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "Normal",
				"price": 500,
				"is_published": True,
			}
		).insert()

		# VIP Ticket 1
		frappe.get_doc(
			{
				"doctype": "Event Ticket",
				"ticket_type": test_vip_ticket_type.name,
				"attendee_name": "John Doe",
				"attendee_email": "john@email.com",
			}
		).insert().submit()

		# VIP Ticket 2 with Normal Ticket 1
		frappe.get_doc(
			{
				"doctype": "Event Booking",
				"user": frappe.session.user,
				"event": test_event.name,
				"attendees": [
					{
						"first_name": "John",
						"last_name": "Doe",
						"ticket_type": test_vip_ticket_type.name,
						"email": "john@email.com",
					},
					{
						"first_name": "Jenny",
						"last_name": "Doe",
						"ticket_type": test_normal_ticket_type.name,
						"email": "jenny@email.com",
					},
				],
			}
		).insert().submit()

		# VIP Ticket 3 with Normal Ticket 2
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Event Booking",
					"user": frappe.session.user,
					"event": test_event.name,
					"attendees": [
						{
							"first_name": "John",
							"last_name": "Doe",
							"ticket_type": test_vip_ticket_type.name,
							"email": "john@email.com",
						},
						{
							"first_name": "John",
							"last_name": "Doe",
							"ticket_type": test_normal_ticket_type.name,
							"email": "john@email.com",
						},
					],
				}
			).insert()

		# Unpublish normal ticket type
		test_normal_ticket_type.is_published = False
		test_normal_ticket_type.save()

		# Booking with unpublished ticket type
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Event Booking",
					"user": frappe.session.user,
					"event": test_event.name,
					"attendees": [
						{
							"first_name": "John",
							"last_name": "Doe",
							"ticket_type": test_normal_ticket_type.name,
							"email": "john@email.com",
						}
					],
				}
			).insert()

	def test_utm_parameters_are_saved(self):
		"""Test that UTM parameters are correctly saved with bookings."""
		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "Standard",
				"price": 100,
			}
		).insert()

		test_booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": test_event.name,
				"user": "Administrator",
				"attendees": [
					{"ticket_type": test_ticket_type.name, "first_name": "John", "email": "john@email.com"},
				],
				"utm_parameters": [
					{"utm_name": "utm_source", "value": "google"},
					{"utm_name": "utm_medium", "value": "cpc"},
					{"utm_name": "utm_campaign", "value": "summer_sale"},
				],
			}
		).insert()

		self.assertEqual(len(test_booking.utm_parameters), 3)
		self.assertEqual(test_booking.utm_parameters[0].utm_name, "utm_source")
		self.assertEqual(test_booking.utm_parameters[0].value, "google")
		self.assertEqual(test_booking.utm_parameters[1].utm_name, "utm_medium")
		self.assertEqual(test_booking.utm_parameters[1].value, "cpc")
		self.assertEqual(test_booking.utm_parameters[2].utm_name, "utm_campaign")
		self.assertEqual(test_booking.utm_parameters[2].value, "summer_sale")

	def test_booking_without_utm_parameters(self):
		"""Test that bookings work correctly without UTM parameters."""
		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "Standard",
				"price": 100,
			}
		).insert()

		test_booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": test_event.name,
				"user": "Administrator",
				"attendees": [
					{"ticket_type": test_ticket_type.name, "first_name": "John", "email": "john@email.com"},
				],
			}
		).insert()

		self.assertEqual(len(test_booking.utm_parameters), 0)

	def test_custom_utm_parameters(self):
		"""Test that custom UTM parameters (beyond standard ones) are saved."""
		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "Standard",
				"price": 100,
			}
		).insert()

		test_booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": test_event.name,
				"user": "Administrator",
				"attendees": [
					{"ticket_type": test_ticket_type.name, "first_name": "John", "email": "john@email.com"},
				],
				"utm_parameters": [
					{"utm_name": "utm_source", "value": "newsletter"},
					{"utm_name": "utm_custom_param", "value": "special_offer"},
				],
			}
		).insert()

		self.assertEqual(len(test_booking.utm_parameters), 2)
		# Check custom utm parameter is saved
		custom_param = next(
			(p for p in test_booking.utm_parameters if p.utm_name == "utm_custom_param"), None
		)
		self.assertIsNotNone(custom_param)
		self.assertEqual(custom_param.value, "special_offer")


class TestProcessBookingAPI(IntegrationTestCase):
	"""Test the process_booking API endpoint for UTM parameter handling."""

	def test_process_booking_with_utm_parameters(self):
		"""Test that process_booking API correctly saves UTM parameters."""
		from buzz.api import process_booking

		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "API Test Ticket",
				"price": 0,  # Free ticket to avoid payment flow
				"is_published": True,
			}
		).insert()

		# Disable tax at event level
		test_event.apply_tax = False
		test_event.save()

		attendees = [
			{
				"first_name": "API Test User",
				"email": "apitest@email.com",
				"ticket_type": str(test_ticket_type.name),
				"add_ons": [],
			}
		]

		utm_parameters = [
			{"utm_name": "utm_source", "value": "facebook"},
			{"utm_name": "utm_medium", "value": "social"},
			{"utm_name": "utm_campaign", "value": "winter_promo"},
			{"utm_name": "utm_content", "value": "banner_ad"},
			{"utm_name": "utm_term", "value": "event tickets"},
		]

		result = process_booking(
			attendees=attendees,
			event=str(test_event.name),
			utm_parameters=utm_parameters,
		)

		# Verify booking was created
		self.assertIn("booking_name", result)

		# Fetch the booking and verify UTM parameters
		booking = frappe.get_doc("Event Booking", result["booking_name"])
		self.assertEqual(len(booking.utm_parameters), 5)

		# Verify each UTM parameter
		utm_dict = {p.utm_name: p.value for p in booking.utm_parameters}
		self.assertEqual(utm_dict["utm_source"], "facebook")
		self.assertEqual(utm_dict["utm_medium"], "social")
		self.assertEqual(utm_dict["utm_campaign"], "winter_promo")
		self.assertEqual(utm_dict["utm_content"], "banner_ad")
		self.assertEqual(utm_dict["utm_term"], "event tickets")

	# ==================== Offline Payment Tests ====================

	def _cleanup_offline_methods(self, event_name):
		"""Remove all Offline Payment Method records for the given event."""
		frappe.db.delete("Offline Payment Method", {"event": event_name})

	def test_offline_booking_cannot_be_submitted_directly(self):
		"""Test that offline bookings cannot be submitted directly — must use approve/reject."""
		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		self._cleanup_offline_methods(test_event.name)

		frappe.get_doc(
			{
				"doctype": "Offline Payment Method",
				"title": "Bank Transfer",
				"event": test_event.name,
				"enabled": 1,
			}
		).insert()

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "Offline Ticket",
				"price": 500,
			}
		).insert()

		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": test_event.name,
				"user": "Administrator",
				"attendees": [
					{"ticket_type": test_ticket_type.name, "first_name": "Test", "email": "test@test.com"}
				],
				"payment_method": "Offline",
			}
		).insert()

		with self.assertRaises(frappe.ValidationError):
			booking.submit()

	def test_approve_offline_booking(self):
		"""Test approving an offline booking submits it and generates tickets."""
		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		self._cleanup_offline_methods(test_event.name)

		frappe.get_doc(
			{
				"doctype": "Offline Payment Method",
				"title": "Bank Transfer",
				"event": test_event.name,
				"enabled": 1,
			}
		).insert()

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "Approval Test Ticket",
				"price": 500,
			}
		).insert()

		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": test_event.name,
				"user": "Administrator",
				"attendees": [
					{"ticket_type": test_ticket_type.name, "first_name": "Test", "email": "test@test.com"}
				],
				"payment_method": "Offline",
				"status": "Approval Pending",
				"payment_status": "Verification Pending",
			}
		).insert()

		# Booking should be in draft with no tickets
		self.assertEqual(booking.docstatus, 0)
		tickets = frappe.db.get_all("Event Ticket", filters={"booking": booking.name})
		self.assertEqual(len(tickets), 0)

		booking.approve_booking()
		booking.reload()

		# After approval, booking should be submitted with tickets generated
		self.assertEqual(booking.docstatus, 1)
		self.assertEqual(booking.status, "Approved")
		self.assertEqual(booking.payment_status, "Paid")

		tickets = frappe.db.get_all("Event Ticket", filters={"booking": booking.name})
		self.assertEqual(len(tickets), 1)

	def test_reject_offline_booking(self):
		"""Test rejecting an offline booking keeps it in draft with no tickets."""
		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		self._cleanup_offline_methods(test_event.name)

		frappe.get_doc(
			{
				"doctype": "Offline Payment Method",
				"title": "Bank Transfer",
				"event": test_event.name,
				"enabled": 1,
			}
		).insert()

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "Rejection Test Ticket",
				"price": 500,
			}
		).insert()

		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": test_event.name,
				"user": "Administrator",
				"attendees": [
					{"ticket_type": test_ticket_type.name, "first_name": "Test", "email": "test@test.com"}
				],
				"payment_method": "Offline",
				"status": "Approval Pending",
				"payment_status": "Verification Pending",
			}
		).insert()

		self.assertEqual(booking.docstatus, 0)

		booking.reject_booking()
		booking.reload()

		# Discarded (docstatus=2) and marked as Rejected
		self.assertEqual(booking.docstatus, 2)
		self.assertEqual(booking.status, "Rejected")

		# No tickets should be generated
		tickets = frappe.db.get_all("Event Ticket", filters={"booking": booking.name})
		self.assertEqual(len(tickets), 0)

	def test_offline_with_coupon_code(self):
		"""Test offline payment with coupon code discount."""
		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		self._cleanup_offline_methods(test_event.name)

		frappe.get_doc(
			{
				"doctype": "Offline Payment Method",
				"title": "Bank Transfer",
				"event": test_event.name,
				"enabled": 1,
			}
		).insert()

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "Coupon Test Ticket",
				"price": 500,
			}
		).insert()

		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"code": f"OFFLINE10-{frappe.generate_hash(length=4)}",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 10,
				"is_active": True,
			}
		).insert()

		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{"ticket_type": test_ticket_type.name, "first_name": "Test", "email": "test@test.com"}
				],
				"payment_method": "Offline",
			}
		).insert()

		self.assertEqual(booking.net_amount, 500)
		self.assertEqual(booking.discount_amount, 50)
		self.assertEqual(booking.total_amount, 450)

	def test_offline_with_tax(self):
		"""Test offline payment with tax calculation."""
		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		test_event.apply_tax = True
		test_event.tax_percentage = 18
		test_event.tax_label = "GST"
		test_event.save()
		self._cleanup_offline_methods(test_event.name)

		frappe.get_doc(
			{
				"doctype": "Offline Payment Method",
				"title": "Bank Transfer",
				"event": test_event.name,
				"enabled": 1,
			}
		).insert()

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "Tax Test Ticket",
				"price": 500,
			}
		).insert()

		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": test_event.name,
				"user": "Administrator",
				"attendees": [
					{"ticket_type": test_ticket_type.name, "first_name": "Test", "email": "test@test.com"}
				],
				"payment_method": "Offline",
			}
		).insert()

		self.assertEqual(booking.net_amount, 500)
		self.assertEqual(booking.tax_percentage, 18)
		self.assertEqual(booking.tax_amount, 90)
		self.assertEqual(booking.total_amount, 590)

	def test_offline_booking_requires_payment_method_field(self):
		"""Test that offline booking requires payment_method field."""
		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		self._cleanup_offline_methods(test_event.name)

		frappe.get_doc(
			{
				"doctype": "Offline Payment Method",
				"title": "Bank Transfer",
				"event": test_event.name,
				"enabled": 1,
			}
		).insert()

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "Payment Method Test",
				"price": 500,
			}
		).insert()

		# Booking without payment_method field should default to normal flow
		booking_without_method = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": test_event.name,
				"user": "Administrator",
				"attendees": [
					{"ticket_type": test_ticket_type.name, "first_name": "Test", "email": "test@test.com"}
				],
			}
		).insert()

		booking_without_method.submit()
		# Without payment_method field, it should go to normal payment flow
		self.assertEqual(booking_without_method.payment_status, "Unpaid")

		# Booking with payment_method = "Offline" should block direct submission
		booking_with_method = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": test_event.name,
				"user": "Administrator",
				"attendees": [
					{"ticket_type": test_ticket_type.name, "first_name": "Test2", "email": "test2@test.com"}
				],
				"payment_method": "Offline",
			}
		).insert()

		with self.assertRaises(frappe.ValidationError):
			booking_with_method.submit()

	def test_process_booking_offline_stays_in_draft(self):
		"""Test that offline bookings via process_booking stay in draft with no tickets."""
		from buzz.api import process_booking

		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		test_event.apply_tax = False
		test_event.is_published = True
		test_event.save()
		self._cleanup_offline_methods(test_event.name)

		offline_method = frappe.get_doc(
			{
				"doctype": "Offline Payment Method",
				"title": "Bank Transfer",
				"event": test_event.name,
				"enabled": 1,
			}
		).insert()

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "Offline Draft Test",
				"price": 500,
				"is_published": True,
			}
		).insert()

		result = process_booking(
			attendees=[
				{
					"first_name": "Offline User",
					"email": "offline@email.com",
					"ticket_type": str(test_ticket_type.name),
					"add_ons": [],
				}
			],
			event=str(test_event.name),
			is_offline=True,
			offline_payment_method=str(offline_method.name),
		)

		self.assertIn("booking_name", result)
		self.assertTrue(result.get("offline_payment"))

		booking = frappe.get_doc("Event Booking", result["booking_name"])

		# Booking must be in draft (not submitted)
		self.assertEqual(booking.docstatus, 0)
		self.assertEqual(booking.status, "Approval Pending")
		self.assertEqual(booking.payment_status, "Verification Pending")

		# No tickets should exist
		tickets = frappe.db.get_all("Event Ticket", filters={"booking": booking.name})
		self.assertEqual(len(tickets), 0)

	def test_process_booking_offline_generates_tickets_on_approval(self):
		"""Test that approving an offline booking created via API generates tickets."""
		from buzz.api import process_booking

		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		test_event.apply_tax = False
		test_event.is_published = True
		test_event.save()
		self._cleanup_offline_methods(test_event.name)

		offline_method = frappe.get_doc(
			{
				"doctype": "Offline Payment Method",
				"title": "Bank Transfer",
				"event": test_event.name,
				"enabled": 1,
			}
		).insert()

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "Offline Approval Test",
				"price": 500,
				"is_published": True,
			}
		).insert()

		result = process_booking(
			attendees=[
				{
					"first_name": "Approval User",
					"email": "approval@email.com",
					"ticket_type": str(test_ticket_type.name),
					"add_ons": [],
				}
			],
			event=str(test_event.name),
			is_offline=True,
			offline_payment_method=str(offline_method.name),
		)

		booking = frappe.get_doc("Event Booking", result["booking_name"])

		# No tickets before approval
		tickets = frappe.db.get_all("Event Ticket", filters={"booking": booking.name})
		self.assertEqual(len(tickets), 0)

		# Approve the booking
		booking.approve_booking()
		booking.reload()

		# After approval: submitted, approved, tickets generated
		self.assertEqual(booking.docstatus, 1)
		self.assertEqual(booking.status, "Approved")
		self.assertEqual(booking.payment_status, "Paid")

		tickets = frappe.db.get_all("Event Ticket", filters={"booking": booking.name})
		self.assertEqual(len(tickets), 1)

	def test_process_booking_free_event_returns_redirect_to(self):
		"""Free bookings (total_amount == 0) must get a redirect_to the new
		token-gated booking-success screen, same as the paid-gateway branch."""
		from buzz.api import process_booking, verify_booking_access_token

		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		test_event.apply_tax = False
		test_event.is_published = True
		test_event.save()

		free_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "Free Redirect Test Ticket",
				"price": 0,
				"is_published": True,
			}
		).insert()

		result = process_booking(
			attendees=[
				{
					"first_name": "Redirect Test User",
					"email": "redirecttest@email.com",
					"ticket_type": str(free_ticket_type.name),
					"add_ons": [],
				}
			],
			event=str(test_event.name),
		)

		self.assertIn("booking_name", result)
		self.assertIn("redirect_to", result)
		self.assertTrue(result["redirect_to"].startswith(f"/booking-success/{result['booking_name']}?token="))

		token = result["redirect_to"].split("token=")[1]
		self.assertTrue(verify_booking_access_token(result["booking_name"], token))

	def test_process_booking_without_utm_parameters(self):
		"""Test that process_booking API works without UTM parameters."""
		from buzz.api import process_booking

		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		test_event.is_published = True
		test_event.save()

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "API Test Ticket No UTM",
				"price": 0,
				"is_published": True,
			}
		).insert()

		# Disable tax at event level
		test_event.apply_tax = False
		test_event.save()

		attendees = [
			{
				"first_name": "No UTM User",
				"email": "noutm@email.com",
				"ticket_type": str(test_ticket_type.name),
				"add_ons": [],
			}
		]

		result = process_booking(
			attendees=attendees,
			event=str(test_event.name),
			utm_parameters=None,
		)

		self.assertIn("booking_name", result)

		booking = frappe.get_doc("Event Booking", result["booking_name"])
		self.assertEqual(len(booking.utm_parameters), 0)

	def test_process_booking_with_empty_utm_parameters(self):
		"""Test that process_booking API handles empty UTM list."""
		from buzz.api import process_booking

		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "API Test Ticket Empty UTM",
				"price": 0,
				"is_published": True,
			}
		).insert()

		# Disable tax at event level
		test_event.apply_tax = False
		test_event.is_published = True
		test_event.save()

		attendees = [
			{
				"first_name": "Empty UTM User",
				"email": "emptyutm@email.com",
				"ticket_type": str(test_ticket_type.name),
				"add_ons": [],
			}
		]

		result = process_booking(
			attendees=attendees,
			event=str(test_event.name),
			utm_parameters=[],
		)

		self.assertIn("booking_name", result)

		booking = frappe.get_doc("Event Booking", result["booking_name"])
		self.assertEqual(len(booking.utm_parameters), 0)

	def test_process_booking_failed_for_unpublished_event(self):
		"""Booking must fail when Buzz Event is not published."""
		from buzz.api import process_booking

		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		test_event.is_published = 0
		test_event.save()

		test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "Unpublished Test Ticket",
				"price": 0,
				"is_published": True,
			}
		).insert()

		attendees = [
			{
				"first_name": "Failed User",
				"email": "failed@email.com",
				"ticket_type": str(test_ticket_type.name),
				"add_ons": [],
			}
		]

		with self.assertRaises(frappe.ValidationError) as ctx:
			process_booking(
				attendees=attendees,
				event=str(test_event.name),
			)

		self.assertIn("Event is not live", str(ctx.exception))

	def test_free_event_booking_auto_confirms(self):
		"""Test that free event bookings (total_amount = 0) automatically confirm on submit."""
		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})

		free_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "Free Ticket",
				"price": 0,
			}
		).insert()

		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": test_event.name,
				"user": frappe.session.user,
				"attendees": [
					{
						"first_name": "Free User",
						"email": "free@email.com",
						"ticket_type": free_ticket_type.name,
					}
				],
			}
		).insert()

		booking.submit()

		self.assertEqual(booking.status, "Confirmed", "Free booking should auto-confirm")
		self.assertEqual(booking.payment_status, "Paid", "Free booking should be marked as Paid")
		self.assertEqual(booking.total_amount, 0, "Free booking should have zero total")


class TestBookingConfirmation(IntegrationTestCase):
	"""Test token-gated guest booking confirmation (issue #167)."""

	def _make_submitted_booking(self):
		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		test_event.apply_tax = False
		test_event.save()

		ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": test_event.name,
				"title": "Confirmation Test Ticket",
				"price": 500,
			}
		).insert()

		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": test_event.name,
				"user": "Administrator",
				"attendees": [
					{"ticket_type": ticket_type.name, "first_name": "Conf", "email": "conf@email.com"}
				],
			}
		).insert()
		booking.submit()
		return booking

	def test_access_token_roundtrip(self):
		from buzz.api import get_booking_access_token, verify_booking_access_token

		token = get_booking_access_token("B-TEST-001")
		self.assertTrue(verify_booking_access_token("B-TEST-001", token))
		# wrong token rejected
		self.assertFalse(verify_booking_access_token("B-TEST-001", "deadbeef"))
		# empty token rejected
		self.assertFalse(verify_booking_access_token("B-TEST-001", ""))
		self.assertFalse(verify_booking_access_token("B-TEST-001", None))
		# token is booking-specific
		self.assertFalse(verify_booking_access_token("B-OTHER-002", token))

	def test_get_booking_confirmation_valid_token_as_guest(self):
		from buzz.api import get_booking_access_token, get_booking_confirmation

		booking = self._make_submitted_booking()
		token = get_booking_access_token(booking.name)

		frappe.set_user("Guest")
		try:
			result = get_booking_confirmation(booking.name, token=token)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(result["booking"]["name"], booking.name)
		self.assertEqual(len(result["tickets"]), 1)
		self.assertEqual(result["tickets"][0]["attendee_name"], "Conf")
		self.assertTrue(result["event"]["title"])

	def test_get_booking_confirmation_bad_token_as_guest_raises(self):
		from buzz.api import get_booking_confirmation

		booking = self._make_submitted_booking()

		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				get_booking_confirmation(booking.name, token="wrong-token")
			with self.assertRaises(frappe.PermissionError):
				get_booking_confirmation(booking.name, token="")
		finally:
			frappe.set_user("Administrator")

	def test_get_booking_confirmation_owner_without_token(self):
		from buzz.api import get_booking_confirmation

		booking = self._make_submitted_booking()

		# Administrator owns/has perm — no token needed
		result = get_booking_confirmation(booking.name)
		self.assertEqual(result["booking"]["name"], booking.name)
