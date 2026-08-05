# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.events.doctype.buzz_team_settings.test_buzz_team_settings import set_team_settings

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class TestSponsorshipEnquiryEmail(IntegrationTestCase):
	"""Tests for Sponsorship Enquiry pitch deck email with template fallback logic."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		cls.test_event.auto_send_pitch_deck = False
		cls.test_event.sponsor_deck_email_template = None
		cls.test_event.sponsor_deck_cc = None
		cls.test_event.sponsor_deck_reply_to = None
		cls.test_event.save()

		set_team_settings(
			cls.test_event.team,
			auto_send_pitch_deck=0,
			default_sponsor_deck_email_template=None,
			default_sponsor_deck_cc=None,
			default_sponsor_deck_reply_to=None,
		)

	def set_team_defaults(self, **values):
		set_team_settings(self.test_event.team, **values)

	def clear_team_defaults(self):
		self.set_team_defaults(
			auto_send_pitch_deck=0,
			default_sponsor_deck_email_template=None,
			default_sponsor_deck_reply_to=None,
			default_sponsor_deck_cc=None,
		)

	def _create_enquiry(self):
		return frappe.get_doc(
			{
				"doctype": "Sponsorship Enquiry",
				"event": self.test_event.name,
				"company_name": "Test Sponsor Co",
				"company_logo": "/files/test-logo.png",
			}
		).insert()

	def _create_template(self, name, subject_prefix):
		if frappe.db.exists("Email Template", name):
			frappe.delete_doc("Email Template", name, force=True)
		return frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": name,
				"subject": f"{subject_prefix} - {{{{ event.title }}}}",
				"response": f"<p>{subject_prefix} content</p>",
			}
		).insert()

	def tearDown(self):
		for e in frappe.get_all("Sponsorship Enquiry", {"company_name": "Test Sponsor Co"}, pluck="name"):
			frappe.delete_doc("Sponsorship Enquiry", e, force=True)

	@classmethod
	def tearDownClass(cls):
		cls.test_event.auto_send_pitch_deck = False
		cls.test_event.sponsor_deck_email_template = None
		cls.test_event.sponsor_deck_cc = None
		cls.test_event.sponsor_deck_reply_to = None
		cls.test_event.save()

		set_team_settings(
			cls.test_event.team,
			auto_send_pitch_deck=0,
			default_sponsor_deck_email_template=None,
			default_sponsor_deck_cc=None,
			default_sponsor_deck_reply_to=None,
		)
		super().tearDownClass()

	@patch("frappe.sendmail")
	def test_no_email_when_disabled(self, mock_sendmail):
		self.test_event.auto_send_pitch_deck = False
		self.test_event.save()

		enquiry = self._create_enquiry()
		enquiry.send_pitch_deck()

		mock_sendmail.assert_not_called()

	@patch("frappe.sendmail")
	def test_uses_event_settings(self, mock_sendmail):
		template = self._create_template("Event Sponsor Template", "EVENT")
		try:
			self.test_event.auto_send_pitch_deck = True
			self.test_event.sponsor_deck_email_template = template.name
			self.test_event.sponsor_deck_reply_to = "event@test.com"
			self.test_event.sponsor_deck_cc = "event-cc@test.com"
			self.test_event.save()

			# after_insert hook triggers send_pitch_deck automatically
			self._create_enquiry()

			mock_sendmail.assert_called_once()
			args = mock_sendmail.call_args[1]
			self.assertIn("EVENT", args["subject"])
			self.assertEqual(args["reply_to"], "event@test.com")
			self.assertEqual(args["cc"], "event-cc@test.com")
		finally:
			self.test_event.auto_send_pitch_deck = False
			self.test_event.sponsor_deck_email_template = None
			self.test_event.sponsor_deck_reply_to = None
			self.test_event.sponsor_deck_cc = None
			self.test_event.save()
			frappe.delete_doc("Email Template", template.name, force=True)

	@patch("frappe.sendmail")
	def test_falls_back_to_team_settings(self, mock_sendmail):
		template = self._create_template("Team Sponsor Template", "TEAM")
		try:
			self.set_team_defaults(
				auto_send_pitch_deck=1,
				default_sponsor_deck_email_template=template.name,
				default_sponsor_deck_reply_to="team@test.com",
				default_sponsor_deck_cc="team-cc@test.com",
			)

			# after_insert hook triggers send_pitch_deck automatically
			self._create_enquiry()

			mock_sendmail.assert_called_once()
			args = mock_sendmail.call_args[1]
			self.assertIn("TEAM", args["subject"])
			self.assertEqual(args["reply_to"], "team@test.com")
			self.assertEqual(args["cc"], "team-cc@test.com")
		finally:
			self.clear_team_defaults()
			frappe.delete_doc("Email Template", template.name, force=True)

	@patch("frappe.sendmail")
	def test_event_settings_take_precedence(self, mock_sendmail):
		event_template = self._create_template("Event Template", "EVENT")
		team_template = self._create_template("Team Template", "TEAM")
		try:
			self.test_event.auto_send_pitch_deck = True
			self.test_event.sponsor_deck_email_template = event_template.name
			self.test_event.sponsor_deck_reply_to = "event@test.com"
			self.test_event.save()

			self.set_team_defaults(
				auto_send_pitch_deck=1,
				default_sponsor_deck_email_template=team_template.name,
				default_sponsor_deck_reply_to="team@test.com",
			)

			# after_insert hook triggers send_pitch_deck automatically
			self._create_enquiry()

			mock_sendmail.assert_called_once()
			args = mock_sendmail.call_args[1]
			self.assertIn("EVENT", args["subject"])
			self.assertEqual(args["reply_to"], "event@test.com")
		finally:
			self.test_event.auto_send_pitch_deck = False
			self.test_event.sponsor_deck_email_template = None
			self.test_event.sponsor_deck_reply_to = None
			self.test_event.save()
			self.clear_team_defaults()
			frappe.delete_doc("Email Template", event_template.name, force=True)
			frappe.delete_doc("Email Template", team_template.name, force=True)
