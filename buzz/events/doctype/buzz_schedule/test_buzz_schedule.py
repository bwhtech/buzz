# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, today

from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzScheduleFactory,
	BuzzScheduleItemTypeFactory,
	BuzzScheduleTrackFactory,
	EventTalkFactory,
)


class TestBuzzSchedule(IntegrationTestCase):
	def setUp(self):
		# One schedule per event, and rollback is per class, so each test gets its own event.
		self.start = add_days(today(), 10)
		self.event = BuzzEventFactory.create(start_date=self.start, end_date=add_days(self.start, 2))
		self.schedule = BuzzScheduleFactory.create(event=str(self.event.name))

	def add_item(self, **row):
		self.schedule.append("items", {"date": self.start, "type": "Break", "all_tracks": 1, **row})
		self.schedule.save()
		return self.schedule.items[-1]

	def test_days_default_to_event_dates(self):
		days = frappe.parse_json(self.schedule.days)
		self.assertEqual([day["label"] for day in days], ["Day 1", "Day 2", "Day 3"])
		self.assertEqual(getdate(days[2]["date"]), getdate(add_days(self.start, 2)))

	def test_item_date_must_be_a_schedule_day(self):
		with self.assertRaises(frappe.ValidationError):
			self.add_item(date=add_days(self.start, 5), start_time="09:00:00", end_time="09:30:00")

	def test_end_time_from_duration(self):
		item = self.add_item(start_time="09:00:00", duration=45 * 60)
		self.assertEqual(str(item.end_time), "9:45:00")

	def test_duration_from_end_time(self):
		item = self.add_item(start_time="09:00:00", end_time="10:30:00")
		self.assertEqual(item.duration, 90 * 60)

	def test_title_from_reference_then_type(self):
		talk = EventTalkFactory.create(event=self.event.name, title="Scaling apps")
		from_talk = self.add_item(
			type="Talk",
			start_time="10:00:00",
			duration=1800,
			reference_doctype="Event Talk",
			reference_document=talk.name,
		)
		from_type = self.add_item(start_time="11:00:00", duration=900)
		self.assertEqual((from_talk.title, from_type.title), ("Scaling apps", "Break"))

	def test_entered_title_is_kept(self):
		item = self.add_item(title="Lunch", start_time="12:00:00", duration=3600)
		self.assertEqual(item.title, "Lunch")

	def test_reference_to_another_events_talk_refused(self):
		talk = EventTalkFactory.create()
		with self.assertRaises(frappe.ValidationError):
			self.add_item(
				start_time="10:00:00",
				duration=1800,
				reference_doctype="Event Talk",
				reference_document=talk.name,
			)

	def test_track_from_another_schedule_refused(self):
		track = BuzzScheduleTrackFactory.create()
		with self.assertRaises(frappe.ValidationError):
			self.add_item(all_tracks=0, track=track.name, start_time="09:00:00", duration=600)

	def test_custom_type_of_another_team_refused(self):
		item_type = BuzzScheduleItemTypeFactory.create()
		with self.assertRaises(frappe.ValidationError):
			self.add_item(type=item_type.name, start_time="09:00:00", duration=600)

	def test_malformed_day_is_refused(self):
		self.schedule.days = frappe.as_json([{"label": "No date"}])
		with self.assertRaises(frappe.ValidationError):
			self.schedule.save()

	def test_event_cannot_change(self):
		self.schedule.event = str(BuzzEventFactory.create().name)
		with self.assertRaises(frappe.ValidationError):
			self.schedule.save()
