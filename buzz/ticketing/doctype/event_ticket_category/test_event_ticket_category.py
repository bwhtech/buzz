# Copyright (c) 2026, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import BuzzEventFactory, EventTicketCategoryFactory, EventTicketTypeFactory


class TestEventTicketCategory(IntegrationTestCase):
	def setUp(self):
		self.event = BuzzEventFactory.create().name
		self.category = EventTicketCategoryFactory.create(event=self.event, title="Workshops")

	def test_rejects_a_duplicate_title_in_the_same_event(self):
		with self.assertRaises(frappe.ValidationError):
			EventTicketCategoryFactory.create(event=self.event, title=" workshops ")

	def test_allows_the_same_title_in_another_event(self):
		EventTicketCategoryFactory.create(title="Workshops")

	def test_ticket_type_accepts_a_category_of_its_event(self):
		ticket_type = EventTicketTypeFactory.create(event=self.event, category=self.category.name)
		self.assertEqual(ticket_type.category, self.category.name)

	def test_ticket_type_rejects_a_category_of_another_event(self):
		with self.assertRaises(frappe.ValidationError):
			EventTicketTypeFactory.create(category=self.category.name)
