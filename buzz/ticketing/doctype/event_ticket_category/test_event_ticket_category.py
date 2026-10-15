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

	def test_saves_changes_to_an_existing_category(self):
		self.category.sort_order = 4
		self.category.save()
		self.assertEqual(frappe.db.get_value("Event Ticket Category", self.category.name, "sort_order"), 4)

	def test_rejects_moving_to_another_event(self):
		self.category.event = BuzzEventFactory.create().name
		with self.assertRaises(frappe.ValidationError):
			self.category.save()

	def test_allows_the_same_title_in_another_event(self):
		EventTicketCategoryFactory.create(title="Workshops")

	def test_ticket_type_accepts_a_category_of_its_event(self):
		ticket_type = EventTicketTypeFactory.create(event=self.event, category=self.category.name)
		self.assertEqual(ticket_type.category, self.category.name)

	def test_ticket_type_rejects_a_category_of_another_event(self):
		with self.assertRaises(frappe.ValidationError):
			EventTicketTypeFactory.create(category=self.category.name)

	def test_deleting_leaves_its_ticket_types_uncategorized(self):
		ticket_type = EventTicketTypeFactory.create(event=self.event, category=self.category.name)
		self.category.delete()
		self.assertIsNone(frappe.db.get_value("Event Ticket Type", ticket_type.name, "category"))
