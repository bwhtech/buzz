from frappe.tests import IntegrationTestCase

from buzz.api.booking.event_data import ticket_type_row
from buzz.tests.factories import BuzzEventFactory, EventTicketTypeFactory


class TestTicketTypeRow(IntegrationTestCase):
	def test_a_sales_count_does_not_reach_the_booking_page(self):
		event = BuzzEventFactory.create()
		ticket_type = EventTicketTypeFactory.create(
			event=event.name,
			max_tickets_available=10,
			prices=[{"currency": "INR", "price": 500}],
		)

		row = ticket_type_row(ticket_type, hold_token=None)

		self.assertNotIn("tickets_sold", row)
		self.assertNotIn("tickets_sold", row["prices"][0])
		self.assertEqual(row.max_tickets_available, 10)
		self.assertEqual(row.prices[0].price, 500)

	def test_the_cached_document_keeps_its_own_fields(self):
		event = BuzzEventFactory.create()
		ticket_type = EventTicketTypeFactory.create(event=event.name, max_tickets_available=10)

		ticket_type_row(ticket_type, hold_token=None)

		self.assertIn("tickets_sold", ticket_type.as_dict())
