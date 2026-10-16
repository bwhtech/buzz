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

	def test_the_same_title_on_one_event_is_refused(self):
		AdditionalEventPageFactory.create(event=self.event, title="FAQ")
		with self.assertRaises(frappe.ValidationError):
			AdditionalEventPageFactory.create(event=self.event, title="FAQ")

	def test_the_same_title_on_another_event_is_allowed(self):
		AdditionalEventPageFactory.create(event=self.event, title="FAQ")
		other_event = BuzzEventFactory.create(team=self.team).name
		self.assertTrue(AdditionalEventPageFactory.create(event=other_event, title="FAQ").name)

	def test_a_team_manager_can_manage_pages(self):
		with self.set_user(self.owner):
			page = AdditionalEventPageFactory.create(event=self.event, title="Travel")
			page.content = "<p>Trains and planes</p>"
			page.save()
			page.delete()

	def test_another_teams_manager_cannot_read_pages(self):
		page = AdditionalEventPageFactory.create(event=self.event, title="Travel")
		outsider = UserFactory.create_once("additional-page-outsider@example.com").name
		BuzzTeamFactory.create_owned_by(outsider, team_name="Other Page Team")
		self.assertFalse(frappe.has_permission("Additional Event Page", "read", doc=page, user=outsider))
