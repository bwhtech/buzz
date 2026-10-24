# Copyright (c) 2026, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.events.doctype.event_check_in_zone.event_check_in_zone import default_zone
from buzz.tests.factories import BuzzEventFactory, EventCheckinZoneFactory


class TestEventCheckinZone(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = BuzzEventFactory.create().name

	def default(self):
		return frappe.get_doc("Event Check-in Zone", default_zone(self.event))

	def test_a_new_event_gets_its_default_zone(self):
		zone = self.default()

		self.assertEqual(zone.title, "Main Entrance")
		self.assertTrue(zone.enabled)

	def test_the_default_zone_cannot_be_deleted(self):
		with self.assertRaises(frappe.ValidationError):
			self.default().delete()

	def test_the_default_zone_cannot_be_disabled(self):
		zone = self.default()
		zone.enabled = 0

		with self.assertRaises(frappe.ValidationError) as raised:
			zone.save()

		self.assertIn("cannot be disabled", str(raised.exception))

	def test_a_zone_can_be_edited(self):
		zone = EventCheckinZoneFactory.create(event=self.event)
		zone.title = "Workshop Hall"
		zone.enabled = 0
		zone.save()

		self.assertEqual(frappe.db.get_value("Event Check-in Zone", zone.name, "title"), "Workshop Hall")

	def test_a_zone_cannot_move_to_another_event(self):
		zone = EventCheckinZoneFactory.create(event=self.event)
		zone.event = BuzzEventFactory.create().name

		with self.assertRaises(frappe.ValidationError):
			zone.save()

	def test_an_event_has_only_one_default_zone(self):
		with self.assertRaises(frappe.ValidationError) as raised:
			EventCheckinZoneFactory.create(event=self.event, is_default=1)

		self.assertIn("already has a default zone", str(raised.exception))

	def test_a_zone_without_check_ins_can_be_deleted(self):
		zone = EventCheckinZoneFactory.create(event=self.event)
		zone.delete()

		self.assertFalse(frappe.db.exists("Event Check-in Zone", zone.name))
