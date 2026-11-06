import frappe

from buzz.api.booking import get_discount, process_booking
from buzz.api.booking.schemas import DiscountQuoteRequest
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

	def test_attendees_share_one_currency_when_the_booking_has_none(self):
		usd_only = self.create_ticket_type(USD_PRICE)
		attendees = [
			{"ticket_type": self.ticket_type, "first_name": "One", "email": "one@example.com"},
			{"ticket_type": usd_only, "first_name": "Two", "email": "two@example.com"},
		]
		booking = EventBookingFactory.build(event=self.event.name, attendees=attendees)

		with self.assertRaises(frappe.ValidationError):
			booking.fetch_amounts_from_ticket_types()

		self.assertEqual({attendee.currency for attendee in booking.attendees}, {"INR"})

	def test_ticket_without_a_usd_price_cannot_be_paid_in_usd(self):
		with self.assertRaises(frappe.ValidationError):
			self.create_booking(currency="USD", ticket_type=self.create_ticket_type(INR_PRICE))

	def test_paid_add_on_cannot_be_paid_in_usd(self):
		add_on = TicketAddOnFactory.create(event=self.event.name, price=200).name
		add_ons = create_add_on_doc("Attendee", [{"add_on": add_on, "value": "M"}])

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(currency="USD", add_ons=add_ons.name)

	def test_percentage_coupon_applies_in_usd(self):
		coupon = BuzzCouponCodeFactory.create(event=self.event.name, discount_percentage=20)

		booking = self.create_booking(currency="USD", coupon_code=coupon.name)

		self.assertEqual(booking.discount_amount, 3)
		self.assertEqual(booking.total_amount, 12)

	def test_flat_coupon_without_a_usd_amount_cannot_be_used_in_usd(self):
		coupon = BuzzCouponCodeFactory.create("flat", event=self.event.name)

		with self.assertRaises(frappe.ValidationError):
			self.create_booking(currency="USD", coupon_code=coupon.name)

	def test_flat_coupon_uses_the_amount_of_the_booking_currency(self):
		amounts = [{"currency": "INR", "price": 100}, {"currency": "USD", "price": 5}]
		coupon = BuzzCouponCodeFactory.create("flat", event=self.event.name, discount_amounts=amounts)

		quote = DiscountQuoteRequest(
			event=str(self.event.name),
			currency="USD",
			ticket_types=[str(self.ticket_type)],
			coupon_code=coupon.code,
		)

		self.assertEqual(get_discount(quote).discount_amount, 5)

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
			self.process_as_booker(request)
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
