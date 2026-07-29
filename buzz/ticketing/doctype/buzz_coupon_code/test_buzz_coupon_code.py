# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.booking import validate_coupon as validate_coupon_endpoint


def validate_coupon(coupon_code, event, user_email=None):
	return validate_coupon_endpoint(coupon_code, event, user_email).__json__()


EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestBuzzCouponCode(IntegrationTestCase):
	"""
	Integration tests for BuzzCouponCode.
	Use this class for testing interactions between multiple components.
	"""

	def setUp(self):
		"""Set up test fixtures."""
		self.test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		self.test_event.apply_tax = False
		self.test_event.save()

		# Create test ticket type
		self.test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": self.test_event.name,
				"title": "Coupon Test Ticket",
				"price": 500,
				"is_published": True,
			}
		).insert()

		# Create test add-on
		self.test_add_on = frappe.get_doc(
			{
				"doctype": "Ticket Add-on",
				"event": self.test_event.name,
				"title": f"Test T-Shirt {frappe.generate_hash(length=6)}",
				"price": 200,
			}
		).insert()

	# ==================== DISCOUNT COUPON TESTS ====================

	def test_percentage_discount_applies_correctly(self):
		"""Test that percentage discount is calculated correctly."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 20,
				"is_active": True,
			}
		).insert()

		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "John Doe",
						"email": "john@test.com",
					},
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "Jane Doe",
						"email": "jane@test.com",
					},
				],
			}
		).insert()

		# 2 tickets x 500 = 1000, 20% discount = 200
		self.assertEqual(booking.net_amount, 1000)
		self.assertEqual(booking.discount_amount, 200)
		self.assertEqual(booking.total_amount, 800)

	def test_flat_discount_applies_correctly(self):
		"""Test that flat amount discount is calculated correctly."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Discount",
				"discount_type": "Flat Amount",
				"discount_value": 300,
				"is_active": True,
			}
		).insert()

		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "John Doe",
						"email": "john@test.com",
					},
				],
			}
		).insert()

		# 1 ticket x 500 = 500, flat 300 discount
		self.assertEqual(booking.net_amount, 500)
		self.assertEqual(booking.discount_amount, 300)
		self.assertEqual(booking.total_amount, 200)

	def test_flat_discount_does_not_exceed_total(self):
		"""Test that flat discount is capped at net amount."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Discount",
				"discount_type": "Flat Amount",
				"discount_value": 1000,  # More than ticket price
				"is_active": True,
			}
		).insert()

		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "John Doe",
						"email": "john@test.com",
					},
				],
			}
		).insert()

		# Discount should be capped at 500 (net amount), not 1000
		self.assertEqual(booking.net_amount, 500)
		self.assertEqual(booking.discount_amount, 500)
		self.assertEqual(booking.total_amount, 0)

	def test_discount_coupon_usage_limit_enforced(self):
		"""Test that discount coupon usage limit is enforced."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 10,
				"max_usage_count": 2,
				"is_active": True,
			}
		).insert()

		# First booking - should succeed
		booking1 = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "User 1",
						"email": "user1@test.com",
					},
				],
			}
		).insert()
		booking1.submit()

		# Second booking - should succeed
		booking2 = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "User 2",
						"email": "user2@test.com",
					},
				],
			}
		).insert()
		booking2.submit()

		# Third booking - should fail (usage limit reached)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Event Booking",
					"event": self.test_event.name,
					"user": "Administrator",
					"coupon_code": coupon.name,
					"attendees": [
						{
							"ticket_type": self.test_ticket_type.name,
							"first_name": "User 3",
							"email": "user3@test.com",
						},
					],
				}
			).insert()

	def test_discount_coupon_unlimited_usage(self):
		"""Test that coupon with max_usage_count=0 has unlimited usage."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 5,
				"max_usage_count": 0,  # Unlimited
				"is_active": True,
			}
		).insert()

		# Create 5 bookings - all should succeed
		for i in range(5):
			booking = frappe.get_doc(
				{
					"doctype": "Event Booking",
					"event": self.test_event.name,
					"user": "Administrator",
					"coupon_code": coupon.name,
					"attendees": [
						{
							"ticket_type": self.test_ticket_type.name,
							"first_name": f"User {i}",
							"email": f"user{i}@test.com",
						},
					],
				}
			).insert()
			booking.submit()

		# Verify all 5 bookings were created
		self.assertEqual(coupon.times_used, 5)

	# ==================== MAX DISCOUNT CAP TESTS ====================

	def test_percentage_discount_capped_at_max(self):
		"""Test that percentage discount is capped at maximum_discount_amount."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 50,
				"maximum_discount_amount": 500,
				"is_active": True,
			}
		).insert()

		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "John Doe",
						"email": "john@test.com",
					},
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "Jane Doe",
						"email": "jane@test.com",
					},
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "Bob Smith",
						"email": "bob@test.com",
					},
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "Alice Brown",
						"email": "alice@test.com",
					},
				],
			}
		).insert()

		# 4 tickets x 500 = 2000, 50% = 1000, but capped at 500
		self.assertEqual(booking.net_amount, 2000)
		self.assertEqual(booking.discount_amount, 500)
		self.assertEqual(booking.total_amount, 1500)

	# ==================== MINIMUM ORDER VALUE TESTS ====================

	def test_min_order_value_enforced(self):
		"""Test that coupon is rejected when order is below minimum_order_value."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 20,
				"minimum_order_value": 1000,
				"is_active": True,
			}
		).insert()

		# Order of 500 (1 ticket) is below minimum of 1000
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Event Booking",
					"event": self.test_event.name,
					"user": "Administrator",
					"coupon_code": coupon.name,
					"attendees": [
						{
							"ticket_type": self.test_ticket_type.name,
							"first_name": "John Doe",
							"email": "john@test.com",
						},
					],
				}
			).insert()

	def test_percentage_with_cap_and_min_order(self):
		"""Test coupon with both maximum_discount_amount and minimum_order_value."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 50,
				"maximum_discount_amount": 300,
				"minimum_order_value": 500,
				"is_active": True,
			}
		).insert()

		# Order of 500 (1 ticket) meets minimum, 50% = 250, below cap
		booking1 = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "John Doe",
						"email": "john@test.com",
					},
				],
			}
		).insert()

		self.assertEqual(booking1.net_amount, 500)
		self.assertEqual(booking1.discount_amount, 250)
		self.assertEqual(booking1.total_amount, 250)

		# Order of 1000 (2 tickets), 50% = 500, capped at 300
		booking2 = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "Jane Doe",
						"email": "jane@test.com",
					},
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "Bob Smith",
						"email": "bob@test.com",
					},
				],
			}
		).insert()

		self.assertEqual(booking2.net_amount, 1000)
		self.assertEqual(booking2.discount_amount, 300)
		self.assertEqual(booking2.total_amount, 700)

	# ==================== FREE TICKETS COUPON TESTS ====================

	def test_free_tickets_applied_correctly(self):
		"""Test that free tickets coupon makes tickets free."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Free Tickets",
				"applies_to": "Event",
				"event": self.test_event.name,
				"ticket_type": self.test_ticket_type.name,
				"number_of_free_tickets": 2,
				"is_active": True,
			}
		).insert()

		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "Speaker 1",
						"email": "speaker1@test.com",
					},
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "Speaker 2",
						"email": "speaker2@test.com",
					},
				],
			}
		).insert()

		# Both tickets should be free
		self.assertEqual(booking.net_amount, 1000)
		self.assertEqual(booking.discount_amount, 1000)
		self.assertEqual(booking.total_amount, 0)

	def test_partial_free_tickets(self):
		"""Test that only N tickets are free when booking more than free limit."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Free Tickets",
				"applies_to": "Event",
				"event": self.test_event.name,
				"ticket_type": self.test_ticket_type.name,
				"number_of_free_tickets": 2,
				"is_active": True,
			}
		).insert()

		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "Person 1",
						"email": "person1@test.com",
					},
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "Person 2",
						"email": "person2@test.com",
					},
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "Person 3",
						"email": "person3@test.com",
					},
				],
			}
		).insert()

		# 3 tickets x 500 = 1500, 2 free = 1000 discount
		self.assertEqual(booking.net_amount, 1500)
		self.assertEqual(booking.discount_amount, 1000)
		self.assertEqual(booking.total_amount, 500)

	def test_partial_free_tickets_with_paid_addon(self):
		"""Test 1 free ticket + 2 attendees + paid add-on."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Free Tickets",
				"applies_to": "Event",
				"event": self.test_event.name,
				"ticket_type": self.test_ticket_type.name,
				"number_of_free_tickets": 1,
				"is_active": True,
				# No free_add_ons - T-Shirt should be paid
			}
		).insert()

		# Create attendee add-on (paid, not in free list)
		attendee_add_on = frappe.get_doc(
			{
				"doctype": "Attendee Ticket Add-on",
				"add_ons": [{"add_on": self.test_add_on.name, "value": "XL"}],
			}
		).insert()

		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "Person 1",
						"email": "person1@test.com",
						"add_ons": attendee_add_on.name,
					},
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "Person 2",
						"email": "person2@test.com",
					},
				],
			}
		).insert()

		# 2 tickets x 500 = 1000, 1 add-on x 200 = 200
		# Net = 1200
		# Only 1 ticket free = 500 discount
		# Total = 700 (1 paid ticket + 1 paid add-on)
		self.assertEqual(booking.net_amount, 1200)
		self.assertEqual(booking.discount_amount, 500)
		self.assertEqual(booking.total_amount, 700)

	def test_free_tickets_tracking_across_bookings(self):
		"""Test that free tickets are tracked across multiple bookings."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Free Tickets",
				"applies_to": "Event",
				"event": self.test_event.name,
				"ticket_type": self.test_ticket_type.name,
				"number_of_free_tickets": 5,
				"is_active": True,
			}
		).insert()

		# First booking: claim 2 free tickets
		booking1 = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "User A1",
						"email": "usera1@test.com",
					},
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "User A2",
						"email": "usera2@test.com",
					},
				],
			}
		).insert()
		booking1.submit()

		# Verify 2 claimed
		self.assertEqual(coupon.free_tickets_claimed, 2)

		# Second booking: claim 2 more (4 total, 1 remaining)
		booking2 = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "User B1",
						"email": "userb1@test.com",
					},
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "User B2",
						"email": "userb2@test.com",
					},
				],
			}
		).insert()
		booking2.submit()

		# Verify 4 claimed
		self.assertEqual(coupon.free_tickets_claimed, 4)

		# Third booking: try to claim 3, but only 1 remaining
		booking3 = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "User C1",
						"email": "userc1@test.com",
					},
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "User C2",
						"email": "userc2@test.com",
					},
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "User C3",
						"email": "userc3@test.com",
					},
				],
			}
		).insert()

		# 3 tickets x 500 = 1500, only 1 free remaining = 500 discount
		self.assertEqual(booking3.discount_amount, 500)
		self.assertEqual(booking3.total_amount, 1000)

	def test_free_tickets_with_free_addons(self):
		"""Test that free add-ons are discounted for free ticket holders."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Free Tickets",
				"applies_to": "Event",
				"event": self.test_event.name,
				"ticket_type": self.test_ticket_type.name,
				"number_of_free_tickets": 1,
				"free_add_ons": [{"add_on": self.test_add_on.name}],
				"is_active": True,
			}
		).insert()

		# Create attendee add-on
		attendee_add_on = frappe.get_doc(
			{
				"doctype": "Attendee Ticket Add-on",
				"add_ons": [{"add_on": self.test_add_on.name, "value": "XL"}],
			}
		).insert()

		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "Speaker",
						"email": "speaker@test.com",
						"add_ons": attendee_add_on.name,
					},
				],
			}
		).insert()

		# Ticket (500) + Add-on (200) = 700, both free
		self.assertEqual(booking.net_amount, 700)
		self.assertEqual(booking.discount_amount, 700)
		self.assertEqual(booking.total_amount, 0)

	# ==================== VALIDATION TESTS ====================

	def test_coupon_event_scope_validation(self):
		"""Test that coupon scoped to event rejects other events."""
		# Get category and host from test event
		category = self.test_event.category
		host = self.test_event.host

		other_event = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": "Other Event",
				"route": "other-event-test",
				"start_date": "2025-12-31",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"category": category,
				"host": host,
			}
		).insert()

		other_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": other_event.name,
				"title": "Other Ticket",
				"price": 100,
				"is_published": True,
			}
		).insert()

		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 10,
				"applies_to": "Event",
				"event": self.test_event.name,  # Scoped to test_event
				"is_active": True,
			}
		).insert()

		# Try to use on other event - should fail
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Event Booking",
					"event": other_event.name,
					"user": "Administrator",
					"coupon_code": coupon.name,
					"attendees": [
						{
							"ticket_type": other_ticket_type.name,
							"first_name": "Test User",
							"email": "test@test.com",
						},
					],
				}
			).insert()

	def test_coupon_category_scope_validation(self):
		"""Test that coupon scoped to event_category applies to events in that category."""
		# Create a different category
		other_category = frappe.get_doc(
			{
				"doctype": "Event Category",
				"name": "Other Test Category",
				"slug": "other-test-category",
			}
		).insert()

		# Create coupon scoped to test_event's category
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 10,
				"applies_to": "Event Category",
				"event_category": self.test_event.category,  # Scoped to category
				"is_active": True,
			}
		).insert()

		# Should work for event in same category
		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "Test User",
						"email": "test@test.com",
					},
				],
			}
		).insert()
		self.assertGreater(booking.discount_amount, 0)

		# Create event in different category
		other_event = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": "Other Category Event",
				"route": "other-category-event-test",
				"start_date": "2025-12-31",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"category": other_category.name,
				"host": self.test_event.host,
			}
		).insert()

		other_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": other_event.name,
				"title": "Other Category Ticket",
				"price": 100,
				"is_published": True,
			}
		).insert()

		# Should fail for event in different category
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Event Booking",
					"event": other_event.name,
					"user": "Administrator",
					"coupon_code": coupon.name,
					"attendees": [
						{
							"ticket_type": other_ticket_type.name,
							"first_name": "Test User",
							"email": "test@test.com",
						},
					],
				}
			).insert()

	def test_coupon_global_scope(self):
		"""Test that coupon with no event/event_category applies to all events."""
		# Create coupon with no event or category (global scope)
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 15,
				"is_active": True,
				# No event or event_category - should apply globally
			}
		).insert()

		# Should work for test_event
		booking1 = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "User 1",
						"email": "user1@test.com",
					},
				],
			}
		).insert()
		self.assertGreater(booking1.discount_amount, 0)

		# Create another event
		other_event = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": "Another Event",
				"route": "another-event-global-test",
				"start_date": "2025-12-31",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"category": self.test_event.category,
				"host": self.test_event.host,
			}
		).insert()

		other_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": other_event.name,
				"title": "Another Event Ticket",
				"price": 200,
				"is_published": True,
			}
		).insert()

		# Should also work for other event (global scope)
		booking2 = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": other_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": other_ticket_type.name,
						"first_name": "User 2",
						"email": "user2@test.com",
					},
				],
			}
		).insert()
		self.assertGreater(booking2.discount_amount, 0)

	def test_inactive_coupon_rejected(self):
		"""Test that inactive coupon is rejected."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 10,
				"is_active": False,  # Inactive
			}
		).insert()

		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Event Booking",
					"event": self.test_event.name,
					"user": "Administrator",
					"coupon_code": coupon.name,
					"attendees": [
						{
							"ticket_type": self.test_ticket_type.name,
							"first_name": "Test User",
							"email": "test@test.com",
						},
					],
				}
			).insert()

	def test_free_tickets_requires_event(self):
		"""Test that Free Tickets coupon requires event."""
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Buzz Coupon Code",
					"coupon_type": "Free Tickets",
					"applies_to": "Event",
					"ticket_type": self.test_ticket_type.name,
					"number_of_free_tickets": 5,
					"is_active": True,
					# No event - should fail
				}
			).insert()

	def test_free_tickets_requires_specific_event_restriction(self):
		"""Test that Free Tickets coupon requires applies_to='Event'."""
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Buzz Coupon Code",
					"coupon_type": "Free Tickets",
					"applies_to": "Event Category",
					"event_category": self.test_event.category,
					"ticket_type": self.test_ticket_type.name,
					"number_of_free_tickets": 2,
					"is_active": True,
				}
			).insert()

	def test_free_tickets_rejects_all_events(self):
		"""Test that Free Tickets coupon cannot use applies_to=''."""
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Buzz Coupon Code",
					"coupon_type": "Free Tickets",
					"applies_to": "",
					"ticket_type": self.test_ticket_type.name,
					"number_of_free_tickets": 2,
					"is_active": True,
				}
			).insert()

	def test_specific_event_clears_event_category(self):
		"""Test that applies_to='Event' clears event_category field."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 10,
				"applies_to": "Event",
				"event": self.test_event.name,
				"event_category": self.test_event.category,  # Should be cleared
				"is_active": True,
			}
		).insert()

		self.assertIsNone(coupon.event_category)

	def test_event_category_clears_event(self):
		"""Test that applies_to='Event Category' clears event field."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 10,
				"applies_to": "Event Category",
				"event": self.test_event.name,  # Should be cleared
				"event_category": self.test_event.category,
				"is_active": True,
			}
		).insert()

		self.assertIsNone(coupon.event)

	def test_all_events_clears_both_scope_fields(self):
		"""Test that applies_to='' clears both event and event_category."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 10,
				"applies_to": "",
				"event": self.test_event.name,  # Should be cleared
				"event_category": self.test_event.category,  # Should be cleared
				"is_active": True,
			}
		).insert()

		self.assertIsNone(coupon.event)
		self.assertIsNone(coupon.event_category)

	def test_percentage_discount_cannot_exceed_100(self):
		"""Test that percentage discount cannot exceed 100%."""
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Buzz Coupon Code",
					"coupon_type": "Discount",
					"discount_type": "Percentage",
					"discount_value": 150,  # More than 100%
					"is_active": True,
				}
			).insert()

	def test_buzz_coupon_code_auto_generated(self):
		"""Test that coupon code is auto-generated if not provided."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 10,
				"is_active": True,
				# No code provided
			}
		).insert()

		self.assertIsNotNone(coupon.code)
		self.assertEqual(len(coupon.code), 8)

	def test_coupon_tracked_in_booking(self):
		"""Test that coupon code is tracked in booking document."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"code": "TESTTRACK",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 10,
				"is_active": True,
			}
		).insert()

		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "Test User",
						"email": "test@test.com",
					},
				],
			}
		).insert()

		# Coupon should be tracked in booking
		self.assertEqual(booking.coupon_code, "TESTTRACK")


class TestValidateCouponAPI(IntegrationTestCase):
	"""Test the validate_coupon API endpoint."""

	def setUp(self):
		self.test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		self.test_ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": self.test_event.name,
				"title": "API Test Ticket",
				"price": 100,
				"is_published": True,
			}
		).insert()

	def test_validate_coupon_returns_discount_info(self):
		"""Test that validate_coupon returns correct discount info."""
		frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"code": "APITEST",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 25,
				"is_active": True,
			}
		).insert()

		result = validate_coupon("APITEST", str(self.test_event.name))

		self.assertTrue(result["valid"])
		self.assertEqual(result["coupon_type"], "Discount")
		self.assertEqual(result["discount_type"], "Percentage")
		self.assertEqual(result["discount_value"], 25)

	def test_validate_coupon_returns_max_and_min_values(self):
		"""Test that validate_coupon returns max_discount_amount and min_order_value."""
		frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"code": "MAXMIN",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 30,
				"maximum_discount_amount": 500,
				"minimum_order_value": 200,
				"is_active": True,
			}
		).insert()

		result = validate_coupon("MAXMIN", str(self.test_event.name))

		self.assertTrue(result["valid"])
		self.assertEqual(result["max_discount_amount"], 500)
		self.assertEqual(result["min_order_value"], 200)

	def test_validate_coupon_returns_free_tickets_info(self):
		"""Test that validate_coupon returns correct free tickets info."""
		frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"code": "FREEAPI",
				"coupon_type": "Free Tickets",
				"applies_to": "Event",
				"event": self.test_event.name,
				"ticket_type": self.test_ticket_type.name,
				"number_of_free_tickets": 3,
				"is_active": True,
			}
		).insert()

		result = validate_coupon("FREEAPI", str(self.test_event.name))

		self.assertTrue(result["valid"])
		self.assertEqual(result["coupon_type"], "Free Tickets")
		self.assertEqual(result["remaining_tickets"], 3)

	def test_validate_coupon_invalid_code(self):
		"""Test that invalid coupon code returns error."""
		result = validate_coupon("INVALIDCODE", str(self.test_event.name))

		self.assertFalse(result["valid"])
		self.assertIn("error", result)

	# ==================== VALIDITY PERIOD TESTS ====================

	def test_coupon_not_yet_active(self):
		"""Test that coupon with future valid_from is rejected."""
		frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"code": "FUTURESTART",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 10,
				"valid_from": frappe.utils.add_days(frappe.utils.today(), 1),
				"is_active": True,
			}
		).insert()

		result = validate_coupon("FUTURESTART", str(self.test_event.name))

		self.assertFalse(result["valid"])
		self.assertIn("not yet active", result["error"].lower())

	def test_expired_coupon_rejected(self):
		"""Test that expired coupon is rejected."""
		frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"code": "EXPIRED",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 10,
				"valid_till": frappe.utils.add_days(frappe.utils.today(), -1),
				"is_active": True,
			}
		).insert()

		result = validate_coupon("EXPIRED", str(self.test_event.name))

		self.assertFalse(result["valid"])
		self.assertIn("expired", result["error"].lower())

	def test_coupon_within_validity_period(self):
		"""Test that coupon within valid date range works."""
		frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"code": "VALIDPERIOD",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 10,
				"valid_from": frappe.utils.add_days(frappe.utils.today(), -1),
				"valid_till": frappe.utils.add_days(frappe.utils.today(), 7),
				"is_active": True,
			}
		).insert()

		result = validate_coupon("VALIDPERIOD", str(self.test_event.name))

		self.assertTrue(result["valid"])

	# ==================== PER-USER LIMIT TESTS ====================

	def test_max_usage_per_user_enforced(self):
		"""Test that user cannot exceed per-user usage limit."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"code": "PERUSER",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 10,
				"max_usage_per_user": 1,
				"is_active": True,
			}
		).insert()

		# Create and submit a booking with this coupon
		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": frappe.session.user,
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "Test User",
						"email": "test@test.com",
					},
				],
			}
		).insert()
		booking.submit()

		# Second attempt should fail
		result = validate_coupon("PERUSER", str(self.test_event.name))

		self.assertFalse(result["valid"])
		self.assertIn("maximum usage limit", result["error"].lower())

	def test_per_user_limit_does_not_affect_other_users(self):
		"""Test that per-user limit doesn't block other users."""
		coupon = frappe.get_doc(
			{
				"doctype": "Buzz Coupon Code",
				"code": "PERUSEROTHER",
				"coupon_type": "Discount",
				"discount_type": "Percentage",
				"discount_value": 10,
				"max_usage_per_user": 1,
				"is_active": True,
			}
		).insert()

		# Create a test user if not exists
		if not frappe.db.exists("User", "testuser_b@example.com"):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": "testuser_b@example.com",
					"first_name": "Test User B",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)

		# User A (Administrator) uses the coupon
		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"coupon_code": coupon.name,
				"attendees": [
					{
						"ticket_type": self.test_ticket_type.name,
						"first_name": "Admin User",
						"email": "admin@test.com",
					},
				],
			}
		).insert()
		booking.submit()

		# Switch to User B
		frappe.set_user("testuser_b@example.com")

		# User B should still be able to use the coupon
		result = validate_coupon("PERUSEROTHER", str(self.test_event.name))

		# Switch back to Administrator
		frappe.set_user("Administrator")

		self.assertTrue(result["valid"])
