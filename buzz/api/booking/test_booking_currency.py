import frappe

from buzz.api.booking import process_booking, validate_coupon
from buzz.api.booking.services import create_add_on_doc
from buzz.tests.base_test_cases import BookingTestCase
from buzz.tests.factories import (
	BuzzCouponCodeFactory,
	EventBookingFactory,
	EventTicketTypeFactory,
	TicketAddOnFactory,
)

INR_PRICE = {"currency": "INR", "price": 1000}
USD_PRICE = {"currency": "USD", "price": 15}


class TestBookingCurrency(BookingTestCase):
	def setUp(self):
		super().setUp()
		self.ticket_type = self.create_ticket_type(INR_PRICE, USD_PRICE)

	def test_usd_booking_charges_the_usd_price(self):
		booking = self.create_booking(currency="USD")

		self.assertEqual(booking.currency, "USD")
		self.assertEqual(booking.attendees[0].amount, 15)
		self.assertEqual(booking.total_amount, 15)

	def test_booking_without_a_currency_charges_the_default_price(self):
		booking = self.create_booking()

		self.assertEqual(booking.currency, "INR")
		self.assertEqual(booking.total_amount, 1000)

	def test_ticket_without_a_usd_price_cannot_be_paid_in_usd(self):
		with self.assertRaises(frappe.ValidationError):
			self.create_booking(currency="USD", ticket_type=self.create_ticket_type(INR_PRICE))

	def test_paid_add_on_cannot_be_paid_in_usd(self):
		add_on = TicketAddOnFactory.create(event=self.event.name, price=200).name
		add_ons = create_add_on_doc("Attendee", [{"add_on": add_on, "value": "M"}])

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(currency="USD", add_ons=add_ons.name)

	def test_percentage_coupon_applies_in_usd(self):
		coupon = BuzzCouponCodeFactory.create(discount_type="Percentage", discount_value=20)

		booking = self.create_booking(currency="USD", coupon_code=coupon.name)

		self.assertEqual(booking.discount_amount, 3)
		self.assertEqual(booking.total_amount, 12)

	def test_flat_coupon_cannot_be_used_in_usd(self):
		coupon = BuzzCouponCodeFactory.create(discount_type="Flat Amount", discount_value=100)

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(currency="USD", coupon_code=coupon.name)

	def test_validate_coupon_refuses_fixed_amount_coupons_in_usd(self):
		capped = BuzzCouponCodeFactory.create(
			discount_type="Percentage", discount_value=20, maximum_discount_amount=500
		).name

		in_usd = validate_coupon(capped, str(self.event.name), None, "USD").__json__()
		in_inr = validate_coupon(capped, str(self.event.name)).__json__()

		self.assertFalse(in_usd["valid"])
		self.assertTrue(in_inr["valid"])

	def test_offline_payment_is_refused_in_usd(self):
		attendee = {
			"first_name": "Booker",
			"email": "booker@example.com",
			"ticket_type": str(self.ticket_type),
		}
		request = self.booking_request(
			attendees=[attendee], currency="USD", is_offline=True, offline_payment_method="Bank Transfer"
		)

		with self.assertRaises(frappe.ValidationError):
			process_booking(request)
		self.assertIn("USD", frappe.local.message_log[-1]["message"])

	def test_free_ticket_can_be_booked_in_usd(self):
		booking = self.create_booking(currency="USD", ticket_type=self.free_ticket_type.name)

		self.assertEqual((booking.currency, booking.total_amount), ("USD", 0))

	def create_ticket_type(self, *prices: dict) -> str:
		return EventTicketTypeFactory.create(event=self.event.name, prices=list(prices)).name

	def create_booking(self, ticket_type=None, add_ons=None, **overrides):
		attendee = {
			"ticket_type": ticket_type or self.ticket_type,
			"first_name": "Attendee",
			"email": "attendee@example.com",
			"add_ons": add_ons,
		}
		return EventBookingFactory.create(event=self.event.name, attendees=[attendee], **overrides)
