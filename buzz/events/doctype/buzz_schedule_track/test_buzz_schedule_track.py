# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe

from buzz.tests.base_test_cases import TeamPermissionTestCase
from buzz.tests.factories import BuzzScheduleFactory, BuzzScheduleTrackFactory


class TestBuzzScheduleTrack(TeamPermissionTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.schedule_a = BuzzScheduleFactory.create(event=str(cls.event_a)).name
		cls.track_a = BuzzScheduleTrackFactory.create(schedule=cls.schedule_a).name

	def test_track_takes_the_event_of_its_schedule(self):
		self.assertEqual(frappe.db.get_value("Buzz Schedule Track", self.track_a, "event"), str(self.event_a))

	def test_other_team_cannot_list_or_read_tracks(self):
		self.assertIn(self.track_a, self.list_as(self.alice, "Buzz Schedule Track"))
		self.assertNotIn(self.track_a, self.list_as(self.bob, "Buzz Schedule Track"))
		self.assertFalse(self.has_permission_as(self.bob, "read", "Buzz Schedule Track", self.track_a))

	def test_other_team_cannot_write_tracks(self):
		self.assertFalse(self.has_permission_as(self.bob, "write", "Buzz Schedule Track", self.track_a))

	def test_other_team_cannot_add_a_track_to_a_schedule(self):
		with self.set_user(self.bob), self.assertRaises(frappe.PermissionError):
			BuzzScheduleTrackFactory.create(schedule=self.schedule_a)

	def test_other_team_cannot_list_or_read_schedules(self):
		self.assertNotIn(self.schedule_a, self.list_as(self.bob, "Buzz Schedule"))
		self.assertFalse(self.has_permission_as(self.bob, "read", "Buzz Schedule", self.schedule_a))
