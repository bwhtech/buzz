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
		self.assertEqual(
			set(row),
			{
				"name",
				"title",
				"event",
				"event_title",
				"start_date",
				"end_date",
				"banner_image",
				"status",
				"creation",
				"modified",
				"speakers",
			},
		)

	def test_rows_carry_their_speakers(self):
		frappe.set_user(self.speaker_user)
		row = next(r for r in serialized_proposals() if r["name"] == self.guest_proposal)
		self.assertEqual(
			row["speakers"],
			[{"first_name": "Speaker", "last_name": None, "email": self.speaker_user}],
		)

	def test_speakers_keep_their_row_order(self):
		proposal = frappe.get_doc(
			{
				"doctype": "Talk Proposal",
				"title": f"Duo Talk {frappe.generate_hash(length=6)}",
				"event": self.event,
				"submitted_by": self.speaker_user,
				"speakers": [
					{"first_name": "First", "email": "first-speaker@example.com"},
					{"first_name": "Second", "email": "second-speaker@example.com"},
				],
			}
		).insert(ignore_permissions=True)

		frappe.set_user(self.speaker_user)
		row = next(r for r in serialized_proposals() if r["name"] == proposal.name)
		self.assertEqual([speaker["first_name"] for speaker in row["speakers"]], ["First", "Second"])

	def test_rows_carry_the_joined_event_columns(self):
		frappe.db.set_value("Buzz Event", self.event, "banner_image", "/files/banner-probe.png")
		self.addCleanup(frappe.clear_document_cache, "Buzz Event", self.event)

		frappe.set_user(self.speaker_user)
		row = next(r for r in serialized_proposals() if r["name"] == self.guest_proposal)
		self.assertEqual(cstr(row["start_date"]), "2030-01-01")
		self.assertEqual(row["banner_image"], "/files/banner-probe.png")

	def test_modified_tracks_the_latest_edit(self):
		proposal = frappe.get_doc("Talk Proposal", self.guest_proposal)
		proposal.title = f"Edited {frappe.generate_hash(length=6)}"
		proposal.save(ignore_permissions=True)
		self.addCleanup(frappe.clear_document_cache, "Talk Proposal", self.guest_proposal)

		frappe.set_user(self.speaker_user)
		row = next(r for r in serialized_proposals() if r["name"] == self.guest_proposal)
		self.assertGreater(row["modified"], row["creation"])

	def test_creation_serializes_in_frappe_datetime_format(self):
		frappe.set_user(self.speaker_user)
		row = next(r for r in serialized_proposals() if r["name"] == self.guest_proposal)
		self.assertRegex(json_handler(row["creation"]), r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
