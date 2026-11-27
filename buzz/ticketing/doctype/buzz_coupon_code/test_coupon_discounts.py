import frappe

from buzz.tests.base_test_cases import CouponTestCase, attendee_rows, create_paid_ticket_type
from buzz.tests.factories import EventBookingFactory


class TestCouponDiscounts(CouponTestCase):
	def test_percentage_discount(self):
		coupon = self.create_coupon(discount_percentage=20).name

		self.assert_amounts(self.create_booking(coupon, count=2), net=1000, discount=200, total=800)

	def test_flat_discount_applies_once_per_order(self):
		coupon = self.create_coupon("flat", discount_amounts=[{"currency": "INR", "price": 300}]).name

		self.assert_amounts(self.create_booking(coupon, count=2), net=1000, discount=300, total=700)

	def test_flat_discount_capped_at_eligible_subtotal(self):
		coupon = self.create_coupon("flat", discount_amounts=[{"currency": "INR", "price": 1000}]).name

		self.assert_amounts(self.create_booking(coupon), net=500, discount=500, total=0)

	def test_add_ons_excluded_from_discount(self):
		coupon = self.create_coupon(discount_percentage=50).name

		self.assert_amounts(self.create_booking_with_add_on(coupon), net=700, discount=250, total=450)

	def test_flat_discount_without_currency_row_is_refused(self):
		coupon = self.create_coupon("flat", discount_amounts=[{"currency": "USD", "price": 10}]).name

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(coupon)

	def test_coupon_is_stored_on_booking(self):
		coupon = self.create_coupon().name

		self.assertEqual(self.create_booking(coupon).coupon_code, coupon)


class TestCouponTicketTypeScope(CouponTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.other_ticket_type = create_paid_ticket_type(cls.event.name, price=1000)

	def create_mixed_booking(self, coupon: str):
		attendees = attendee_rows(self.ticket_type.name, 1) + attendee_rows(self.other_ticket_type.name, 1)
		return EventBookingFactory.create(event=self.event.name, coupon_code=coupon, attendees=attendees)

	def create_scoped_coupon(self, *traits, **overrides):
		rows = [{"ticket_type": self.ticket_type.name}]
		return self.create_coupon(*traits, applies_to_all_ticket_types=0, ticket_types=rows, **overrides)

	def test_percentage_applies_to_scoped_tickets_only(self):
		coupon = self.create_scoped_coupon(discount_percentage=50).name

		self.assert_amounts(self.create_mixed_booking(coupon), net=1500, discount=250, total=1250)

	def test_flat_capped_at_scoped_subtotal(self):
		coupon = self.create_scoped_coupon("flat", discount_amounts=[{"currency": "INR", "price": 800}]).name

		self.assert_amounts(self.create_mixed_booking(coupon), net=1500, discount=500, total=1000)

	def test_no_eligible_ticket_is_refused(self):
		rows = [{"ticket_type": self.other_ticket_type.name}]
		coupon = self.create_coupon(applies_to_all_ticket_types=0, ticket_types=rows).name

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(coupon)


class TestCouponMinimum(CouponTestCase):
	def create_minimum_amount_coupon(self, amount: int):
		rows = [{"currency": "INR", "price": amount}]
		return self.create_coupon(minimum_requirement="Minimum Order Amount", minimum_order_amounts=rows).name

	def test_minimum_amount_met_exactly(self):
		coupon = self.create_minimum_amount_coupon(1000)

		self.assert_amounts(self.create_booking(coupon, count=2), net=1000, discount=100, total=900)

	def test_minimum_amount_below_threshold_refused(self):
		coupon = self.create_minimum_amount_coupon(1000)

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(coupon)

	def test_minimum_amount_above_threshold(self):
		coupon = self.create_minimum_amount_coupon(1000)

		self.assert_amounts(self.create_booking(coupon, count=3), net=1500, discount=150, total=1350)

	def test_minimum_amount_ignores_add_ons(self):
		coupon = self.create_minimum_amount_coupon(600)

		with self.assertRaises(frappe.ValidationError):
			self.create_booking_with_add_on(coupon)

	def test_minimum_amount_without_currency_row_refused(self):
		rows = [{"currency": "USD", "price": 10}]
		coupon = self.create_coupon(minimum_requirement="Minimum Order Amount", minimum_order_amounts=rows)

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(coupon.name, count=3)

	def test_minimum_ticket_count(self):
		coupon = self.create_coupon(minimum_requirement="Minimum Ticket Count", minimum_ticket_count=2).name

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(coupon)
		self.assert_amounts(self.create_booking(coupon, count=2), net=1000, discount=100, total=900)
		self.assert_amounts(self.create_booking(coupon, count=3), net=1500, discount=150, total=1350)
