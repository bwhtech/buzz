# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, EventTicketTypeFactory, TicketAddOnFactory


class TestTicketAddOnScope(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = BuzzEventFactory.create()

	def test_ticket_type_of_the_event_is_accepted(self):
		ticket_type = EventTicketTypeFactory.create(event=self.event.name).name
		add_on = TicketAddOnFactory.create(event=self.event.name, ticket_types=[{"ticket_type": ticket_type}])
		self.assertEqual([str(row.ticket_type) for row in add_on.ticket_types], [str(ticket_type)])

	def test_ticket_type_of_another_event_is_refused(self):
		ticket_type = EventTicketTypeFactory.create().name
		with self.assertRaises(frappe.ValidationError):
			TicketAddOnFactory.create(event=self.event.name, ticket_types=[{"ticket_type": ticket_type}])
