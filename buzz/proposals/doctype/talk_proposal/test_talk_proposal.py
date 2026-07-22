# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.test_forms import ensure_prompt_named_record

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


def make_test_user(email: str, roles: list[str] | None = None) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
	user = frappe.get_doc("User", email)
	user.add_roles("Buzz User", *(roles or []))
	return user.name


def make_test_event(category: str, host: str) -> str:
	event = frappe.new_doc("Buzz Event")
	event.update(
		{
			"title": f"Proposal Perm Event {frappe.generate_hash(length=6)}",
			"start_date": "2030-01-01",
			"end_date": "2030-01-01",
			"start_time": "10:00:00",
			"end_time": "18:00:00",
			"medium": "Online",
			"category": category,
			"host": host,
			"is_published": 1,
		}
	)
	event.insert(ignore_permissions=True)
	return event.name


def make_guest_proposal(event: str, speaker_email: str, title: str | None = None) -> str:
	"""Simulate a guest form submission: owner and submitted_by both end up 'Guest'."""
	original_user = frappe.session.user
	frappe.set_user("Guest")
	try:
		proposal = frappe.get_doc(
			{
				"doctype": "Talk Proposal",
				"title": title or f"Guest Talk {frappe.generate_hash(length=6)}",
				"event": event,
				"speakers": [{"first_name": "Speaker", "email": speaker_email}],
			}
		).insert(ignore_permissions=True)
	finally:
		frappe.set_user(original_user)
	return proposal.name


class TestTalkProposalSpeakerAccess(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.category = ensure_prompt_named_record("Event Category", "Proposal Perm Category")
		cls.host = ensure_prompt_named_record("Event Host", "Proposal Perm Host")
		cls.event = make_test_event(cls.category, cls.host)
		cls.speaker_user = make_test_user("speaker-perm@example.com")
		cls.other_user = make_test_user("other-perm@example.com")
		cls.manager_user = make_test_user("manager-perm@example.com", roles=["Event Manager"])
		cls.guest_proposal = make_guest_proposal(cls.event, cls.speaker_user)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_speaker_can_read_guest_submitted_proposal(self):
		frappe.set_user(self.speaker_user)
		proposal = frappe.get_doc("Talk Proposal", self.guest_proposal)
		self.assertTrue(proposal.has_permission("read"))

	def test_speaker_can_write_guest_submitted_proposal(self):
		frappe.set_user(self.speaker_user)
		proposal = frappe.get_doc("Talk Proposal", self.guest_proposal)
		self.assertTrue(proposal.has_permission("write"))

	def test_speaker_sees_guest_submitted_proposal_in_list(self):
		frappe.set_user(self.speaker_user)
		names = frappe.get_list("Talk Proposal", pluck="name")
		self.assertIn(self.guest_proposal, names)

	def test_non_speaker_cannot_read_or_list_proposal(self):
		frappe.set_user(self.other_user)
		proposal = frappe.get_doc("Talk Proposal", self.guest_proposal)
		self.assertFalse(proposal.has_permission("read"))
		self.assertFalse(proposal.has_permission("write"))
		self.assertNotIn(self.guest_proposal, frappe.get_list("Talk Proposal", pluck="name"))

	def test_submitter_sees_proposal_even_without_speaker_row(self):
		proposal = frappe.get_doc(
			{
				"doctype": "Talk Proposal",
				"title": f"Submitter Talk {frappe.generate_hash(length=6)}",
				"event": self.event,
				"submitted_by": self.speaker_user,
				"speakers": [{"first_name": "Someone", "email": "someone-else@example.com"}],
			}
		).insert(ignore_permissions=True)

		frappe.set_user(self.speaker_user)
		self.assertIn(proposal.name, frappe.get_list("Talk Proposal", pluck="name"))
		self.assertTrue(proposal.has_permission("read"))

	def test_event_manager_sees_all_proposals(self):
		frappe.set_user(self.manager_user)
		self.assertIn(self.guest_proposal, frappe.get_list("Talk Proposal", pluck="name"))
