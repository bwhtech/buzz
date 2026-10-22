from unittest.mock import patch
from urllib.parse import urlparse

import frappe
from frappe.tests import IntegrationTestCase

from buzz import analytics
from buzz.api.playground.services import create_sandbox

ENABLED = {"posthog_api_key": "phc_test", "posthog_force_enabled": 1}
PLAYGROUND = {"buzz_playground": 1, "mute_emails": 1}


class TestPosthogGate(IntegrationTestCase):
	def test_off_without_a_key(self):
		with patch.dict(frappe.conf, {"posthog_api_key": None, "posthog_force_enabled": 1}):
			self.assertIsNone(analytics.posthog_config())

	def test_off_in_developer_mode(self):
		with patch.dict(
			frappe.conf, {"posthog_api_key": "phc_test", "posthog_force_enabled": 0, "developer_mode": 1}
		):
			self.assertFalse(analytics.is_enabled())

	def test_follows_the_telemetry_opt_out(self):
		conf = {"posthog_api_key": "phc_test", "posthog_force_enabled": 0, "developer_mode": 0}
		with patch.dict(frappe.conf, conf), patch("frappe.get_system_settings", return_value=0):
			self.assertFalse(analytics.is_enabled())
		with patch.dict(frappe.conf, conf), patch("frappe.get_system_settings", return_value=1):
			self.assertTrue(analytics.is_enabled())


class TestPosthogConfig(IntegrationTestCase):
	def setUp(self):
		self.enterContext(patch.dict(frappe.conf, {**ENABLED, **PLAYGROUND}))

	def test_identifies_the_sandbox_and_persona(self):
		sandbox = create_sandbox()
		with self.set_user(sandbox.attendee):
			config = analytics.posthog_config()

		self.assertEqual(config["sandbox"], sandbox.name)
		self.assertEqual(config["persona"], "attendee")
		self.assertEqual(config["host"], analytics.DEFAULT_HOST)

	def test_anonymous_outside_a_sandbox(self):
		config = analytics.posthog_config()
		self.assertIsNone(config["sandbox"])
		self.assertIsNone(config["persona"])


class TestCapture(IntegrationTestCase):
	def test_queues_the_event_after_commit(self):
		with patch.dict(frappe.conf, ENABLED), patch("frappe.enqueue") as enqueue:
			analytics.capture("playground_started", "sandbox-1", {"sandbox": "sandbox-1"})

		enqueue.assert_called_once()
		self.assertTrue(enqueue.call_args.kwargs["enqueue_after_commit"])
		self.assertEqual(enqueue.call_args.kwargs["payload"]["distinct_id"], "sandbox-1")
		properties = enqueue.call_args.kwargs["payload"]["properties"]
		self.assertEqual(properties["$host"], urlparse(frappe.utils.get_url()).netloc)

	def test_sends_nothing_without_a_key(self):
		with patch.dict(frappe.conf, {"posthog_api_key": None}), patch("frappe.enqueue") as enqueue:
			analytics.capture("playground_started", "sandbox-1")
		enqueue.assert_not_called()

	def test_never_raises(self):
		with patch.dict(frappe.conf, ENABLED), patch("frappe.enqueue", side_effect=RuntimeError):
			analytics.capture("playground_started", "sandbox-1")
