# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.events.test_events import create_event
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user
from buzz.patches.set_event_venue_name import execute as set_event_venue_name


class IntegrationTestEventVenue(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.team = create_owned_team("Venue Naming Team", create_user("venue-naming@example.com", "Owner"))

	def create_venue(self, venue_name: str):
		return frappe.get_doc(
			{
				"doctype": "Event Venue",
				"venue_name": venue_name,
				"address": "1 Test Street",
				"team": self.team,
			}
		).insert(ignore_permissions=True)

	def test_name_is_random_and_venue_name_is_the_label(self):
		venue = self.create_venue("Town Hall")

		self.assertNotEqual(venue.name, "Town Hall")
		self.assertEqual(venue.get_title(), "Town Hall")

	def test_two_venues_can_share_a_venue_name(self):
		self.assertNotEqual(self.create_venue("Shared Hall").name, self.create_venue("Shared Hall").name)

	def test_event_carries_the_venue_name_and_follows_a_change(self):
		venue = self.create_venue("Old Hall")
		event = create_event("Venue Name Event", self.team, venue=venue.name)
		self.assertEqual(frappe.db.get_value("Buzz Event", event, "venue_name"), "Old Hall")

		venue.venue_name = "New Hall"
		venue.save(ignore_permissions=True)

		self.assertEqual(frappe.db.get_value("Buzz Event", event, "venue_name"), "New Hall")

	def test_patch_copies_the_old_docname_into_venue_name(self):
		venue = self.create_venue("Legacy Hall")
		event = create_event("Legacy Venue Event", self.team, venue=venue.name)
		frappe.db.set_value("Event Venue", venue.name, "venue_name", "", update_modified=False)
		frappe.db.set_value("Buzz Event", event, "venue_name", "", update_modified=False)

		set_event_venue_name()

		self.assertEqual(frappe.db.get_value("Event Venue", venue.name, "venue_name"), venue.name)
		self.assertEqual(frappe.db.get_value("Buzz Event", event, "venue_name"), venue.name)
