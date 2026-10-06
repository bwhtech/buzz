from frappe.tests import IntegrationTestCase

from buzz.api.booking.services import create_add_on_doc
from buzz.tests.factories import (
	BuzzEventFactory,
	EventBookingFactory,
	EventTicketTypeFactory,
	TicketAddOnFactory,
)

TICKET_PRICE = 500
ADD_ON_PRICE = 200


class CouponTestCase(IntegrationTestCase):
	"""An event with a paid ticket type and a paid add-on, booked with a coupon."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = BuzzEventFactory.create()
		cls.ticket_type = create_paid_ticket_type(cls.event.name)
		cls.add_on = TicketAddOnFactory.create(event=cls.event.name, price=ADD_ON_PRICE)

	def book(self, coupon: str, count: int = 1, **overrides):
		attendees = attendee_rows(self.ticket_type.name, count)
		return EventBookingFactory.create(
			event=self.event.name, coupon_code=coupon, attendees=attendees, **overrides
		)

	def book_with_add_on(self, coupon: str, count: int = 1):
		attendees = attendee_rows(self.ticket_type.name, count)
		add_ons = create_add_on_doc(attendees[0]["first_name"], [{"add_on": self.add_on.name, "value": "XL"}])
		attendees[0]["add_ons"] = add_ons.name
		return EventBookingFactory.create(event=self.event.name, coupon_code=coupon, attendees=attendees)

	def assert_amounts(self, booking, net: int, discount: int, total: int):
		amounts = (booking.net_amount, booking.discount_amount, booking.total_amount)
		self.assertEqual(amounts, (net, discount, total))


def create_paid_ticket_type(event, price: int = TICKET_PRICE):
	return EventTicketTypeFactory.create(event=event, prices=[{"currency": "INR", "price": price}])


def attendee_rows(ticket_type, count: int) -> list[dict]:
	return [
		{
			"ticket_type": ticket_type,
			"first_name": f"Attendee {index}",
			"email": f"attendee{index}@example.com",
		}
		for index in range(count)
	]
