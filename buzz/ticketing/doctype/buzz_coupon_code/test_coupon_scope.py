import frappe

from buzz.tests.factories import BuzzCouponCodeFactory, BuzzEventFactory, EventBookingFactory
from buzz.ticketing.doctype.buzz_coupon_code.coupon_test_case import (
	CouponTestCase,
	attendee_rows,
	create_paid_ticket_type,
)


class TestCouponScope(CouponTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# A new event comes with a new category, so it is outside both scopes of `event`.
		cls.other_event = BuzzEventFactory.create()
		cls.other_ticket_type = create_paid_ticket_type(cls.other_event.name, price=100)

	def test_coupon_event_scope_validation(self):
		coupon = self.create_coupon(applies_to="Event", event=self.event.name)

		with self.assertRaises(frappe.ValidationError):
			self.create_other_event_booking(coupon)

	def test_coupon_category_scope_validation(self):
		coupon = self.create_coupon(applies_to="Event Category", event_category=self.event.category)

		self.assert_amounts(self.create_booking(coupon), net=500, discount=50, total=450)
		with self.assertRaises(frappe.ValidationError):
			self.create_other_event_booking(coupon)

	def test_coupon_global_scope(self):
		coupon = self.create_coupon()

		self.assertEqual(self.create_booking(coupon).discount_amount, 50)
		self.assertEqual(self.create_other_event_booking(coupon).discount_amount, 10)

	def test_specific_event_clears_event_category(self):
		coupon = BuzzCouponCodeFactory.create(
			applies_to="Event", event=self.event.name, event_category=self.event.category
		)

		self.assertIsNone(coupon.event_category)

	def test_event_category_clears_event(self):
		coupon = BuzzCouponCodeFactory.create(
			applies_to="Event Category", event=self.event.name, event_category=self.event.category
		)

		self.assertIsNone(coupon.event)

	def test_all_events_clears_both_scope_fields(self):
		coupon = BuzzCouponCodeFactory.create(
			applies_to="", event=self.event.name, event_category=self.event.category
		)

		self.assertEqual((coupon.event, coupon.event_category), (None, None))

	def create_coupon(self, **overrides) -> str:
		return BuzzCouponCodeFactory.create("percentage", discount_value=10, **overrides).name

	def create_other_event_booking(self, coupon: str):
		attendees = attendee_rows(self.other_ticket_type.name, 1)
		return EventBookingFactory.create(
			event=self.other_event.name, coupon_code=coupon, attendees=attendees
		)
