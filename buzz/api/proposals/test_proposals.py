import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils.data import cstr
from frappe.utils.response import json_handler

from buzz.api.forms.test_forms import ensure_prompt_named_record
from buzz.api.proposals import get_my_proposals
from buzz.proposals.doctype.talk_proposal.test_talk_proposal import (
	make_guest_proposal,
	make_test_event,
	make_test_user,
)


def serialized_proposals() -> list[dict]:
	return [proposal.__json__() for proposal in get_my_proposals()]


class TestGetMyProposals(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.category = ensure_prompt_named_record("Event Category", "My Proposals Category")
		cls.host = ensure_prompt_named_record("Event Host", "My Proposals Host")
		cls.event = make_test_event(cls.category, cls.host)
		cls.speaker_user = make_test_user("speaker-api@example.com")
		cls.other_user = make_test_user("other-api@example.com")
		cls.guest_proposal = make_guest_proposal(cls.event, cls.speaker_user)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_returns_guest_submitted_proposal_for_speaker(self):
		frappe.set_user(self.speaker_user)
		names = [row["name"] for row in serialized_proposals()]
		self.assertIn(self.guest_proposal, names)

	def test_returns_proposal_submitted_by_user_without_speaker_row(self):
		proposal = frappe.get_doc(
			{
				"doctype": "Talk Proposal",
				"title": f"Submitter API Talk {frappe.generate_hash(length=6)}",
				"event": self.event,
				"submitted_by": self.speaker_user,
				"speakers": [{"first_name": "Someone", "email": "someone-else@example.com"}],
			}
		).insert(ignore_permissions=True)

		frappe.set_user(self.speaker_user)
		names = [row["name"] for row in serialized_proposals()]
		self.assertIn(proposal.name, names)

	def test_excludes_unrelated_proposals(self):
		frappe.set_user(self.other_user)
		names = [row["name"] for row in serialized_proposals()]
		self.assertNotIn(self.guest_proposal, names)

	def test_rows_have_expected_shape(self):
		frappe.set_user(self.speaker_user)
		row = next(r for r in serialized_proposals() if r["name"] == self.guest_proposal)
		self.assertEqual(row["event"], cstr(self.event))
		self.assertEqual(row["status"], "Review Pending")
		self.assertEqual(set(row), {"name", "title", "event", "event_title", "status", "creation"})

	def test_creation_serializes_in_frappe_datetime_format(self):
		frappe.set_user(self.speaker_user)
		row = next(r for r in serialized_proposals() if r["name"] == self.guest_proposal)
		self.assertRegex(json_handler(row["creation"]), r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
