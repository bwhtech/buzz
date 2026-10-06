import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today
from frappe.utils.data import cstr
from frappe.utils.response import json_handler

from buzz.api.proposals import accept_proposal, get_my_proposals
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, TalkProposalFactory, UserFactory


class ProposalTestCase(IntegrationTestCase):
	@classmethod
	def create_guest_proposal(cls, event: str, speaker_email: str) -> str:
		"""The public form's submission: `owner` and `submitted_by` are both Guest."""
		with cls.set_user("Guest"):
			proposal = TalkProposalFactory.create(
				"guest_submitted",
				event=event,
				speakers=[{"first_name": "Speaker", "email": speaker_email}],
				flags={"ignore_permissions": True},
			)
		return proposal.name


class TestGetMyProposals(ProposalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.start_date = add_days(today(), 30)
		cls.event = str(BuzzEventFactory.create(start_date=cls.start_date, end_date=cls.start_date).name)
		cls.speaker_user = UserFactory.create_once("speaker-api@example.com").name
		cls.other_user = UserFactory.create_once("other-api@example.com").name
		cls.guest_proposal = cls.create_guest_proposal(cls.event, cls.speaker_user)

	def test_returns_guest_submitted_proposal_for_speaker(self):
		self.assertIn(self.guest_proposal, self.listed_names(self.speaker_user))

	def test_returns_proposal_submitted_by_user_without_speaker_row(self):
		proposal = TalkProposalFactory.create(
			event=self.event,
			submitted_by=self.speaker_user,
			speakers=[{"first_name": "Someone", "email": "someone-else@example.com"}],
		)

		self.assertIn(proposal.name, self.listed_names(self.speaker_user))

	def test_excludes_unrelated_proposals(self):
		self.assertNotIn(self.guest_proposal, self.listed_names(self.other_user))

	def test_rows_carry_their_speakers(self):
		row = self.listed_row(self.guest_proposal)

		self.assertEqual(row["event"], cstr(self.event))
		self.assertEqual(row["status"], "Review Pending")
		self.assertEqual(
			row["speakers"],
			[{"first_name": "Speaker", "last_name": None, "email": self.speaker_user}],
		)

	def test_speakers_keep_their_row_order(self):
		proposal = TalkProposalFactory.create(
			event=self.event,
			submitted_by=self.speaker_user,
			speakers=[
				{"first_name": "First", "email": "first-speaker@example.com"},
				{"first_name": "Second", "email": "second-speaker@example.com"},
			],
		)

		row = self.listed_row(proposal.name)
		self.assertEqual([speaker["first_name"] for speaker in row["speakers"]], ["First", "Second"])

	def test_rows_carry_the_joined_event_columns(self):
		frappe.db.set_value("Buzz Event", self.event, "banner_image", "/files/banner-probe.png")
		self.addCleanup(frappe.clear_document_cache, "Buzz Event", self.event)

		row = self.listed_row(self.guest_proposal)
		self.assertEqual(cstr(row["start_date"]), self.start_date)
		self.assertEqual(row["banner_image"], "/files/banner-probe.png")

	def test_modified_tracks_the_latest_edit(self):
		proposal = frappe.get_doc("Talk Proposal", self.guest_proposal)
		proposal.title = f"Edited {frappe.generate_hash(length=6)}"
		proposal.save(ignore_permissions=True)
		self.addCleanup(frappe.clear_document_cache, "Talk Proposal", self.guest_proposal)

		row = self.listed_row(self.guest_proposal)
		self.assertGreater(row["modified"], row["creation"])

	def test_creation_serializes_in_frappe_datetime_format(self):
		row = self.listed_row(self.guest_proposal)
		self.assertRegex(json_handler(row["creation"]), r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")

	def listed_names(self, user: str) -> list[str]:
		with self.set_user(user):
			return [proposal.name for proposal in get_my_proposals()]

	def listed_row(self, proposal: str) -> dict:
		with self.set_user(self.speaker_user):
			rows = [row.__json__() for row in get_my_proposals()]
		return next(row for row in rows if row["name"] == proposal)


class TestAcceptProposal(ProposalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.manager = UserFactory.create_once("accept-manager@example.com").name
		cls.outsider = UserFactory.create_once("accept-outsider@example.com").name
		cls.speaker = UserFactory.create_once("accept-speaker@example.com").name
		team = BuzzTeamFactory.create_owned_by(cls.manager).name
		cls.event = str(BuzzEventFactory.create(team=team).name)

	def setUp(self):
		self.proposal = self.create_guest_proposal(self.event, self.speaker)

	def test_accepting_creates_the_talk_and_sets_the_status(self):
		with self.set_user(self.manager):
			accepted = accept_proposal(self.proposal)

		self.assertEqual(accepted.status, "Accepted")
		self.assertEqual(frappe.db.get_value("Talk Proposal", self.proposal, "status"), "Accepted")
		self.assertEqual(frappe.db.get_value("Event Talk", accepted.talk, "proposal"), self.proposal)

	def test_the_talk_carries_the_proposal_speakers(self):
		with self.set_user(self.manager):
			talk = frappe.get_doc("Event Talk", accept_proposal(self.proposal).talk)

		self.assertEqual(len(talk.speakers), 1)

	def test_accepting_twice_reuses_the_talk_rather_than_duplicating_it(self):
		with self.set_user(self.manager):
			first = accept_proposal(self.proposal)
			frappe.db.set_value("Talk Proposal", self.proposal, "status", "Shortlisted")
			second = accept_proposal(self.proposal)

		self.assertEqual(second.talk, first.talk)
		self.assertEqual(second.status, "Accepted")
		self.assertEqual(frappe.db.count("Event Talk", {"proposal": self.proposal}), 1)

	def test_a_speaker_cannot_accept_their_own_proposal(self):
		# A listed speaker holds write on the document; accepting is the team's call.
		with self.set_user(self.speaker), self.assertRaises(frappe.PermissionError):
			accept_proposal(self.proposal)

	def test_an_outsider_cannot_accept(self):
		with self.set_user(self.outsider), self.assertRaises(frappe.PermissionError):
			accept_proposal(self.proposal)
