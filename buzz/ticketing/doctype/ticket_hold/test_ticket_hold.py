# Copyright (c) 2026, BWH Studios and Contributors
# See license.txt

from frappe.utils import add_to_date, now_datetime

from buzz.tests.base_test_cases import BookingTestCase
from buzz.tests.factories import EventTicketFactory, EventTicketTypeFactory, TicketHoldFactory


class TestTicketHoldAvailability(BookingTestCase):
	def setUp(self):
		super().setUp()
		self.ticket_type = EventTicketTypeFactory.create(event=self.event.name, max_tickets_available=10)

	def hold(self, *traits, **overrides):
		return TicketHoldFactory.create(*traits, ticket_type=self.ticket_type.name, **overrides)

	def test_remaining_leaves_out_sold_and_live_held_tickets(self):
		EventTicketFactory.create("submitted", event=self.event.name, ticket_type=self.ticket_type.name)
		self.hold(quantity=3)
		self.hold("expired", quantity=4)

		self.assertEqual(self.ticket_type.remaining_tickets, 6)

	def test_remaining_counts_every_hold_but_the_callers(self):
		mine = self.hold(quantity=3)
		self.hold(quantity=2)

		self.assertEqual(self.ticket_type.get_remaining_tickets(hold_token=mine.hold_token), 8)

	def test_a_hold_stops_counting_when_it_expires(self):
		expires_at = add_to_date(now_datetime(), minutes=10)
		self.hold(quantity=4, expires_at=expires_at)

		with self.freeze_time(add_to_date(expires_at, seconds=-1)):
			self.assertEqual(self.ticket_type.remaining_tickets, 6)
		with self.freeze_time(expires_at):
			self.assertEqual(self.ticket_type.remaining_tickets, 10)

	def test_ticket_types_without_a_limit_ignore_holds(self):
		unlimited = EventTicketTypeFactory.create(event=self.event.name)
		TicketHoldFactory.create(ticket_type=unlimited.name, quantity=5)

		self.assertEqual(unlimited.remaining_tickets, -1)
