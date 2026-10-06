import json
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from buzz import telemetry, telemetry_scan
from buzz.tests.factories import BuzzEventFactory
from buzz.tests.telemetry_capture import capturing, properties_of


class TestTelemetryWrapper(IntegrationTestCase):
	def test_capture_adds_app_and_shared_properties(self):
		with capturing() as mock_capture:
			telemetry.capture("thing_happened", {"kind": "a"}, interval="1d")

		mock_capture.assert_called_once()
		self.assertEqual(mock_capture.call_args.args, ("thing_happened", "buzz"))
		self.assertEqual(mock_capture.call_args.kwargs["interval"], "1d")
		properties = mock_capture.call_args.kwargs["properties"]
		self.assertEqual(properties["kind"], "a")
		self.assertEqual(properties["app_version"], frappe.get_attr("buzz.__version__"))
		self.assertIn(properties["entry"], {"system", "api", "desk", "dashboard", "website", "import"})

	def test_capture_is_silent_during_system_writes(self):
		for flag in ("in_install", "in_migrate", "in_patch", "in_fixtures"):
			with self.subTest(flag=flag), capturing() as mock_capture:
				frappe.flags[flag] = True
				try:
					telemetry.capture("thing_happened")
				finally:
					frappe.flags[flag] = False
				mock_capture.assert_not_called()

	def test_capture_never_raises(self):
		with (
			patch("buzz.telemetry.is_enabled", return_value=True),
			patch("buzz.telemetry.frappe_capture", side_effect=RuntimeError("pulse down")),
		):
			telemetry.capture("thing_happened")
			frappe.db.after_commit.run()

	def test_rolled_back_capture_is_never_sent(self):
		with capturing() as mock_capture:
			telemetry.capture("thing_happened")
			frappe.db.rollback()
		mock_capture.assert_not_called()

	def test_capture_waits_for_commit(self):
		with (
			patch("buzz.telemetry.is_enabled", return_value=True),
			patch("buzz.telemetry.frappe_capture") as mock_capture,
		):
			telemetry.capture("thing_happened")
			mock_capture.assert_not_called()
			telemetry.capture("page_seen", on_commit=False)
			mock_capture.assert_called_once()
			frappe.db.after_commit.reset()


class TestTelemetryHelpers(UnitTestCase):
	def test_entry_from_referrer(self):
		cases = {
			"http://site/app/buzz-event/1": "desk",
			"http://site/b/tickets": "dashboard",
			"http://site/b": "dashboard",
			"http://site/apps/list": "website",
			"http://site/application": "website",
			"http://site/blog/post": "website",
			"http://site/events/my-event": "website",
			"": "api",
		}
		self.addCleanup(setattr, frappe.local, "request", getattr(frappe.local, "request", None))
		for referrer, expected in cases.items():
			with self.subTest(referrer=referrer):
				frappe.local.request = SimpleNamespace(headers={"Referer": referrer})
				self.assertEqual(telemetry.get_entry(), expected)

	def test_entry_for_import(self):
		frappe.flags.in_import = True
		self.addCleanup(setattr, frappe.flags, "in_import", False)

		self.assertEqual(telemetry.get_entry(), "import")

	def test_count_bucket(self):
		cases = {
			0: "0",
			1: "1",
			2: "2-5",
			5: "2-5",
			6: "6-20",
			20: "6-20",
			21: "21-100",
			100: "21-100",
			101: "101+",
		}
		for count, expected in cases.items():
			with self.subTest(count=count):
				self.assertEqual(telemetry.count_bucket(count), expected)


class TestSiteProfile(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		BuzzEventFactory.create()

	def test_nothing_is_queried_when_telemetry_is_off(self):
		with (
			patch("buzz.telemetry_scan.is_enabled", return_value=False),
			patch("buzz.telemetry_scan.get_site_profile") as mock_profile,
			capturing() as mock_capture,
		):
			telemetry_scan.send_site_profile()

		mock_profile.assert_not_called()
		mock_capture.assert_not_called()

	def test_site_profile_is_sent_when_telemetry_is_on(self):
		with (
			patch("buzz.telemetry_scan.is_enabled", return_value=True),
			capturing() as mock_capture,
		):
			telemetry_scan.send_site_profile()

		properties = properties_of(mock_capture, "site_profile")
		self.assertGreaterEqual(properties["events"], 1)
		self.assertIn("bookings_per_event_median", properties)
		self.assertIn("payment_gateways", properties)
		self.assertLess(len(json.dumps(properties)), 4096)

	def test_site_profile_values_are_counts_not_names(self):
		profile = telemetry_scan.get_site_profile()
		for key, value in profile.items():
			with self.subTest(key=key):
				self.assertTrue(value is None or isinstance(value, int | float), f"{key}={value!r}")

	def test_missing_table_degrades_to_zero(self):
		with patch("frappe.db.count", side_effect=Exception("table missing")):
			counts = telemetry_scan.get_record_counts()
		self.assertTrue(all(value == 0 for value in counts.values()))
