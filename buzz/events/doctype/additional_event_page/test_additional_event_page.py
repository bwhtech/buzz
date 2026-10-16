# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import (
	AdditionalEventPageFactory,
	BuzzEventFactory,
	BuzzTeamFactory,
	UserFactory,
)


class IntegrationTestAdditionalEventPage(IntegrationTestCase):
	def setUp(self):
		self.owner = UserFactory.create_once("additional-page-owner@example.com").name
		self.team = BuzzTeamFactory.create_owned_by(self.owner, team_name="Page Team").name
		self.event = BuzzEventFactory.create(team=self.team).name

	def test_route_follows_the_title(self):
		page = AdditionalEventPageFactory.create(event=self.event, title="Travel & Stay")
		self.assertEqual(page.route, "travel-stay")

		page.title = "Getting there"
		page.save()
		self.assertEqual(page.route, "getting-there")

	def test_the_same_title_on_one_event_is_refused(self):
		AdditionalEventPageFactory.create(event=self.event, title="FAQ")
		with self.assertRaises(frappe.ValidationError):
			AdditionalEventPageFactory.create(event=self.event, title="FAQ")

	def test_the_same_title_on_another_event_is_allowed(self):
		AdditionalEventPageFactory.create(event=self.event, title="FAQ")
		other_event = BuzzEventFactory.create(team=self.team).name
		self.assertTrue(AdditionalEventPageFactory.create(event=other_event, title="FAQ").name)

	def test_a_title_with_no_letters_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			AdditionalEventPageFactory.create(event=self.event, title="!!!")

	def test_a_team_manager_can_manage_pages(self):
		with self.set_user(self.owner):
			page = frappe.get_doc(
				{
					"doctype": "Additional Event Page",
					"event": self.event,
					"title": "Travel",
					"content": "<p>How to get there</p>",
				}
			).insert()
			page.content = "<p>Trains and planes</p>"
			page.save()
			page.delete()

	def test_an_outsider_cannot_read_pages(self):
		AdditionalEventPageFactory.create(event=self.event, title="Travel")
		outsider = UserFactory.create_once("additional-page-outsider@example.com").name
		self.assertFalse(frappe.has_permission("Additional Event Page", "read", user=outsider))
