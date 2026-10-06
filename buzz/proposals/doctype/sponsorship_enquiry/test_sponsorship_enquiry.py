# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	EmailTemplateFactory,
	SponsorshipEnquiryFactory,
)


class TestSponsorshipEnquiryEmail(IntegrationTestCase):
	def test_no_email_when_disabled(self):
		event = BuzzEventFactory.create(auto_send_pitch_deck=0)
		BuzzTeamFactory.set_settings(event.team, {"auto_send_pitch_deck": 0})

		with patch("frappe.sendmail") as sendmail:
			SponsorshipEnquiryFactory.create(event=event.name).send_pitch_deck()

		sendmail.assert_not_called()

	def test_uses_event_settings(self):
		event = BuzzEventFactory.create(
			auto_send_pitch_deck=1,
			sponsor_deck_email_template=self.create_template("EVENT"),
			sponsor_deck_reply_to="event@test.com",
			sponsor_deck_cc="event-cc@test.com",
		)

		email = self.email_sent_on_enquiry(event)

		self.assertIn("EVENT", email["subject"])
		self.assertEqual(email["reply_to"], "event@test.com")
		self.assertEqual(email["cc"], "event-cc@test.com")

	def test_falls_back_to_team_settings(self):
		event = BuzzEventFactory.create(auto_send_pitch_deck=0)
		BuzzTeamFactory.set_settings(
			event.team,
			{
				"auto_send_pitch_deck": 1,
				"default_sponsor_deck_email_template": self.create_template("TEAM"),
				"default_sponsor_deck_reply_to": "team@test.com",
				"default_sponsor_deck_cc": "team-cc@test.com",
			},
		)

		email = self.email_sent_on_enquiry(event)

		self.assertIn("TEAM", email["subject"])
		self.assertEqual(email["reply_to"], "team@test.com")
		self.assertEqual(email["cc"], "team-cc@test.com")

	def test_event_settings_take_precedence(self):
		event = BuzzEventFactory.create(
			auto_send_pitch_deck=1,
			sponsor_deck_email_template=self.create_template("EVENT"),
			sponsor_deck_reply_to="event@test.com",
		)
		BuzzTeamFactory.set_settings(
			event.team,
			{
				"auto_send_pitch_deck": 1,
				"default_sponsor_deck_email_template": self.create_template("TEAM"),
				"default_sponsor_deck_reply_to": "team@test.com",
			},
		)

		email = self.email_sent_on_enquiry(event)

		self.assertIn("EVENT", email["subject"])
		self.assertEqual(email["reply_to"], "event@test.com")

	def create_template(self, subject_prefix: str) -> str:
		return EmailTemplateFactory.create(
			subject=f"{subject_prefix} - {{{{ event.title }}}}",
			response=f"<p>{subject_prefix} content</p>",
		).name

	def email_sent_on_enquiry(self, event) -> dict:
		"""The `after_insert` hook sends the pitch deck."""
		with patch("frappe.sendmail") as sendmail:
			SponsorshipEnquiryFactory.create(event=event.name)

		sendmail.assert_called_once()
		return sendmail.call_args[1]


class TestSponsorshipApprovalNotification(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = BuzzEventFactory.create().name

	def test_an_account_holder_is_sent_to_their_dashboard(self):
		enquiry = self.create_enquiry()

		message = self.approval_email(enquiry)["args"]["message"]

		self.assertIn(f"/b/account/sponsorships/{enquiry.name}", message)

	def test_a_guest_enquiry_is_not_sent_to_a_page_it_cannot_open(self):
		enquiry = self.create_enquiry(owner="Guest", contact_email="guest-applicant@example.com")

		email = self.approval_email(enquiry)

		self.assertEqual(email["recipients"], ["guest-applicant@example.com"])
		# Nobody satisfies is_applicant on a Guest-owned enquiry, so the link would 403.
		self.assertNotIn("/b/account/sponsorships/", email["args"]["message"])
		self.assertIn("be in touch", email["args"]["message"])

	def test_a_guest_enquiry_without_a_contact_email_sends_nothing(self):
		enquiry = self.create_enquiry(owner="Guest")

		with patch("frappe.sendmail") as sendmail:
			enquiry.send_approval_notification()

		sendmail.assert_not_called()

	def create_enquiry(self, owner: str | None = None, contact_email: str | None = None):
		enquiry = SponsorshipEnquiryFactory.create(event=self.event, contact_email=contact_email)
		if owner:
			frappe.db.set_value("Sponsorship Enquiry", enquiry.name, "owner", owner)
			enquiry.reload()
		return enquiry

	def approval_email(self, enquiry) -> dict:
		with patch("frappe.sendmail") as sendmail:
			enquiry.send_approval_notification()
		return sendmail.call_args[1]
