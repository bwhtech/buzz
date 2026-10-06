import frappe

from buzz.tests.factories import BuzzCouponCodeFactory
from buzz.ticketing.doctype.buzz_coupon_code.coupon_test_case import CouponTestCase


class TestFreeTicketsCoupon(CouponTestCase):
	def test_free_tickets_applied_correctly(self):
		coupon = self.create_coupon(number_of_free_tickets=2)

		self.assert_amounts(self.book(coupon, count=2), net=1000, discount=1000, total=0)

	def test_partial_free_tickets(self):
		coupon = self.create_coupon(number_of_free_tickets=2)

		self.assert_amounts(self.book(coupon, count=3), net=1500, discount=1000, total=500)

	def test_partial_free_tickets_with_paid_addon(self):
		coupon = self.create_coupon(number_of_free_tickets=1)

		booking = self.book_with_add_on(coupon, count=2)

		self.assert_amounts(booking, net=1200, discount=500, total=700)

	def test_free_tickets_tracking_across_bookings(self):
		coupon = self.create_coupon(number_of_free_tickets=5)

		self.book(coupon, count=2).submit()
		self.assertEqual(self.claimed(coupon), 2)
		self.book(coupon, count=2).submit()
		self.assertEqual(self.claimed(coupon), 4)

		booking = self.book(coupon, count=3)
		self.assertEqual((booking.discount_amount, booking.total_amount), (500, 1000))

	def test_free_tickets_with_free_addons(self):
		coupon = self.create_coupon(number_of_free_tickets=1, free_add_ons=[{"add_on": self.add_on.name}])

		self.assert_amounts(self.book_with_add_on(coupon), net=700, discount=700, total=0)

	def test_free_tickets_requires_event(self):
		with self.assertRaises(frappe.ValidationError):
			self.create_coupon(event=None)

	def test_free_tickets_requires_specific_event_restriction(self):
		with self.assertRaises(frappe.ValidationError):
			self.create_coupon(applies_to="Event Category", event_category=self.event.category)

	def test_free_tickets_rejects_all_events(self):
		with self.assertRaises(frappe.ValidationError):
			self.create_coupon(applies_to="")

	def create_coupon(self, **overrides) -> str:
		values = {"event": self.event.name, "ticket_type": self.ticket_type.name, **overrides}
		return BuzzCouponCodeFactory.create("free_tickets", **values).name

	def claimed(self, coupon: str) -> int:
		return frappe.get_doc("Buzz Coupon Code", coupon).free_tickets_claimed
