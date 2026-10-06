from datetime import date, datetime, timezone

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import getdate

from buzz.patches.set_time_zone_label_for_existing_events import execute as backfill_time_zone_labels
from buzz.tests.factories import BuzzEventFactory
from buzz.utils import get_time_zone_label

# The label is a pure function of its arguments, so a fixed date never expires.
REFERENCE_DATETIME = datetime(2026, 6, 15, 12, 0)


class TestTimeZoneLabel(UnitTestCase):
	def test_tzdb_abbreviation_when_alphabetic(self):
		self.assert_labels(
			{"Asia/Kolkata": "IST", "Asia/Tokyo": "JST", "Africa/Nairobi": "EAT", "UTC": "UTC"}
		)

	def test_dst_variant_follows_reference_date(self):
		winter = datetime(2026, 1, 15, 12, 0)
		summer = datetime(2026, 7, 15, 12, 0)
		self.assertEqual(get_time_zone_label("America/New_York", winter), "EST")
		self.assertEqual(get_time_zone_label("America/New_York", summer), "EDT")
		self.assertEqual(get_time_zone_label("Europe/Berlin", winter), "CET")
		self.assertEqual(get_time_zone_label("Europe/Berlin", summer), "CEST")

	def test_curated_abbreviation_when_tzdb_is_numeric(self):
		self.assert_labels(
			{"Asia/Dubai": "GST", "Asia/Riyadh": "AST", "Asia/Bangkok": "ICT", "Asia/Kathmandu": "NPT"}
		)

	def test_gmt_offset_fallback_for_unmapped_zone(self):
		self.assert_labels(
			{"Asia/Thimphu": "GMT+6", "Asia/Yangon": "GMT+6:30", "Pacific/Marquesas": "GMT-9:30"}
		)

	def test_empty_or_invalid_time_zone_returns_empty(self):
		self.assert_labels({None: "", "": "", "Not/A_Zone": ""})

	def test_current_iana_names_for_renamed_zones(self):
		self.assert_labels({"Asia/Ho_Chi_Minh": "ICT", "America/Nuuk": "WGT"})

	def test_aware_reference_datetime_converted_not_reinterpreted(self):
		# US DST ends 2026-11-01 06:00 UTC, so 05:30 UTC is still 01:30 EDT.
		aware_reference = datetime(2026, 11, 1, 5, 30, tzinfo=timezone.utc)
		self.assertEqual(get_time_zone_label("America/New_York", aware_reference), "EDT")

	def assert_labels(self, expected: dict):
		for time_zone, label in expected.items():
			with self.subTest(time_zone=time_zone):
				self.assertEqual(get_time_zone_label(time_zone, REFERENCE_DATETIME), label)


class TestEventTimeZoneLabelField(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		event = BuzzEventFactory.create()
		cls.event_links = {"team": event.team, "host": event.host, "category": event.category}

	def test_label_set_on_insert(self):
		self.assertEqual(self.create_event(time_zone="Asia/Kolkata").time_zone_label, "IST")

	def test_label_updates_when_time_zone_changes(self):
		event = self.create_event(time_zone="Asia/Kolkata")
		event.time_zone = "Asia/Dubai"
		event.save()
		self.assertEqual(event.time_zone_label, "GST")

	def test_label_cleared_when_time_zone_removed(self):
		event = self.create_event(time_zone="Asia/Kolkata")
		event.time_zone = ""
		event.save()
		self.assertEqual(event.time_zone_label, "")

	def test_label_uses_event_start_date_for_dst(self):
		next_july = str(date(getdate().year + 1, 7, 10))
		event = self.create_event(time_zone="America/New_York", start_date=next_july, end_date=next_july)
		self.assertEqual(event.time_zone_label, "EDT")

	def test_backfill_patch_skips_events_missing_start_fields(self):
		event = self.create_event(time_zone="Asia/Kolkata")
		frappe.db.set_value(
			"Buzz Event", event.name, {"start_time": None, "time_zone_label": ""}, update_modified=False
		)

		backfill_time_zone_labels()

		self.assertEqual(frappe.db.get_value("Buzz Event", event.name, "time_zone_label"), "")

	def create_event(self, **fields):
		return BuzzEventFactory.create(**self.event_links, **fields)
