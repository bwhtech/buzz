# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, EventTicketTypeFactory, TicketAddOnFactory
from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import PAID_EVENTS_FLAG


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


class TestTicketAddOnPaidEventsFlag(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = BuzzEventFactory.create()

	def setUp(self):
		BuzzTeamFactory.set_settings(self.event.team, {PAID_EVENTS_FLAG: 0})
		self.addCleanup(BuzzTeamFactory.set_settings, self.event.team, {PAID_EVENTS_FLAG: 1})

	def test_free_add_on_saves_without_the_flag(self):
		TicketAddOnFactory.create(event=self.event.name)

	def test_paid_add_on_needs_the_flag(self):
		with self.assertRaises(frappe.ValidationError):
			TicketAddOnFactory.create(event=self.event.name, price=500)

	def test_existing_paid_add_on_stays_editable_after_the_flag_is_off(self):
		BuzzTeamFactory.set_settings(self.event.team, {PAID_EVENTS_FLAG: 1})
		add_on = TicketAddOnFactory.create(event=self.event.name, price=500)
		BuzzTeamFactory.set_settings(self.event.team, {PAID_EVENTS_FLAG: 0})
		add_on.title = "Renamed"
		add_on.save()
