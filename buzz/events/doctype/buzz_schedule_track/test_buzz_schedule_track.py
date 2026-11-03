# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe

from buzz.tests.base_test_cases import TeamPermissionTestCase
from buzz.tests.factories import BuzzScheduleFactory, BuzzScheduleTrackFactory

STANDARD_TRACK = "Main Track"


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

	def test_every_team_lists_the_standard_track_and_only_its_own_tracks(self):
		for user in (self.alice, self.bob):
			self.assertIn(STANDARD_TRACK, self.list_as(user, "Buzz Schedule Track"))
			self.assertTrue(self.has_permission_as(user, "read", "Buzz Schedule Track", STANDARD_TRACK))
		self.assertIn(self.track_a, self.list_as(self.alice, "Buzz Schedule Track"))
		self.assertNotIn(self.track_a, self.list_as(self.bob, "Buzz Schedule Track"))

	def test_teams_cannot_change_the_standard_track(self):
		for ptype in ("write", "delete"):
			self.assertFalse(self.has_permission_as(self.alice, ptype, "Buzz Schedule Track", STANDARD_TRACK))
		self.assertTrue(
			self.has_permission_as("Administrator", "write", "Buzz Schedule Track", STANDARD_TRACK)
		)

	def test_other_team_cannot_list_or_read_schedules(self):
		self.assertNotIn(self.schedule_a, self.list_as(self.bob, "Buzz Schedule"))
		self.assertFalse(self.has_permission_as(self.bob, "read", "Buzz Schedule", self.schedule_a))
