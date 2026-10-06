from frappe.tests import IntegrationTestCase

from buzz.api.booking.services import create_add_on_doc
from buzz.tests.factories import (
	BuzzEventFactory,
	EventBookingFactory,
	EventTicketTypeFactory,
	TicketAddOnFactory,
)

TICKET_PRICE = 500
ADD_ON_PRICE = 100


class TestBookingTotals(IntegrationTestCase):
	def test_total_without_taxes_includes_add_ons(self):
		event = BuzzEventFactory.create().name
		booking = self.create_booking(event, TICKET_PRICE, attendees=2)
		self.assertEqual(booking.total_amount, 1000)

		add_on = TicketAddOnFactory.create(event=event, price=ADD_ON_PRICE).name
		booking.attendees[0].add_ons = create_add_on_doc("John", [{"add_on": add_on, "value": "XL"}]).name
		booking.save()

		self.assertEqual(booking.attendees[0].number_of_add_ons, 1)
		self.assertEqual(booking.attendees[0].add_on_total, ADD_ON_PRICE)
		self.assertEqual((booking.net_amount, booking.total_amount), (1100, 1100))

	def test_exclusive_tax_is_added_on_top(self):
		event = BuzzEventFactory.create("with_tax", tax_label="GST", tax_percentage=18).name

		booking = self.create_booking(event, TICKET_PRICE, attendees=2)

		self.assertEqual((booking.tax_label, booking.tax_percentage), ("GST", 18))
		self.assertEqual((booking.net_amount, booking.tax_amount, booking.total_amount), (1000, 180, 1180))

	def test_custom_tax_label(self):
		event = BuzzEventFactory.create("with_tax", tax_label="VAT", tax_percentage=20).name

		booking = self.create_booking(event, 100)

		self.assertEqual((booking.tax_label, booking.tax_percentage), ("VAT", 20))
		self.assertEqual((booking.tax_amount, booking.total_amount), (20, 120))

	def test_inclusive_tax_is_back_calculated_without_raising_the_total(self):
		event = BuzzEventFactory.create("with_tax", tax_inclusive=1, tax_percentage=18).name

		booking = self.create_booking(event, TICKET_PRICE, attendees=2)

		self.assertEqual(booking.net_amount, 1000)
		self.assertAlmostEqual(booking.tax_amount, round(1000 * 18 / 118, 2), places=2)
		self.assertEqual(booking.total_amount, 1000)

	def create_booking(self, event: str, price: float, attendees: int = 1):
		ticket_type = EventTicketTypeFactory.create(event=event, prices=[{"currency": "INR", "price": price}])
		rows = [
			{"ticket_type": ticket_type.name, "first_name": name, "email": f"{name.lower()}@example.com"}
			for name in ("John", "Jenny")[:attendees]
		]
		return EventBookingFactory.create(event=event, attendees=rows)
