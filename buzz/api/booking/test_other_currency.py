import frappe

from buzz.api.booking import process_booking, validate_coupon
from buzz.api.booking.services import create_add_on_doc
from buzz.api.booking.test_booking import BookingTestCase


class TestOtherCurrencyBooking(BookingTestCase):
	def setUp(self):
		super().setUp()
		self.ticket_type = self.make_ticket_type(usd_price=15)

	def make_ticket_type(self, usd_price=None):
		return frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": self.event.name,
				"title": f"Currency Ticket {frappe.generate_hash(length=6)}",
				"price": 1000,
				"is_published": 1,
				"prices": [{"currency": "USD", "price": usd_price}] if usd_price else [],
			}
		).insert(ignore_permissions=True)

	def make_coupon(self, **values):
		return frappe.get_doc(
			{"doctype": "Buzz Coupon Code", "coupon_type": "Discount", "is_active": 1, **values}
		).insert(ignore_permissions=True)

	def make_booking(self, currency=None, ticket_type=None, coupon=None, add_ons=None):
		return frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.event.name,
				"user": "Administrator",
				"currency": currency,
				"coupon_code": coupon.name if coupon else None,
				"attendees": [
					{
						"ticket_type": (ticket_type or self.ticket_type).name,
						"first_name": "Attendee",
						"email": "attendee@example.com",
						"add_ons": add_ons,
					}
				],
			}
		).insert(ignore_permissions=True)

	def test_usd_booking_charges_the_usd_price(self):
		booking = self.make_booking(currency="USD")

		self.assertEqual(booking.currency, "USD")
		self.assertEqual(booking.attendees[0].amount, 15)
		self.assertEqual(booking.total_amount, 15)

	def test_booking_without_a_currency_charges_inr(self):
		booking = self.make_booking()

		self.assertEqual(booking.currency, "INR")
		self.assertEqual(booking.total_amount, 1000)

	def test_ticket_without_a_usd_price_cannot_be_paid_in_usd(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_booking(currency="USD", ticket_type=self.make_ticket_type())

	def test_paid_add_on_cannot_be_paid_in_usd(self):
		add_on = frappe.get_doc(
			{"doctype": "Ticket Add-on", "event": self.event.name, "title": "T-shirt", "price": 200}
		).insert(ignore_permissions=True)
		add_ons = create_add_on_doc("Attendee", [{"add_on": add_on.name, "value": "M"}])

		with self.assertRaises(frappe.ValidationError):
			self.make_booking(currency="USD", add_ons=add_ons.name)

	def test_percentage_coupon_applies_in_usd(self):
		coupon = self.make_coupon(discount_type="Percentage", discount_value=20)

		booking = self.make_booking(currency="USD", coupon=coupon)

		self.assertEqual(booking.discount_amount, 3)
		self.assertEqual(booking.total_amount, 12)

	def test_flat_coupon_cannot_be_used_in_usd(self):
		coupon = self.make_coupon(discount_type="Flat Amount", discount_value=100)

		with self.assertRaises(frappe.ValidationError):
			self.make_booking(currency="USD", coupon=coupon)

	def test_validate_coupon_refuses_fixed_amount_coupons_in_usd(self):
		capped = self.make_coupon(discount_type="Percentage", discount_value=20, maximum_discount_amount=500)

		in_usd = validate_coupon(capped.name, str(self.event.name), None, "USD").__json__()
		in_inr = validate_coupon(capped.name, str(self.event.name)).__json__()

		self.assertFalse(in_usd["valid"])
		self.assertTrue(in_inr["valid"])

	def test_offline_payment_is_refused_in_usd(self):
		request = self.booking_request(
			attendees=[
				{
					"first_name": "Booker",
					"email": "booker@example.com",
					"ticket_type": str(self.ticket_type.name),
				}
			],
			currency="USD",
			is_offline=True,
			offline_payment_method="Bank Transfer",
		)

		with self.assertRaises(frappe.ValidationError):
			process_booking(request)
		self.assertIn("USD", frappe.local.message_log[-1]["message"])

	def test_free_ticket_can_be_booked_in_usd(self):
		booking = self.make_booking(currency="USD", ticket_type=self.free_ticket_type)

		self.assertEqual((booking.currency, booking.total_amount), ("USD", 0))
