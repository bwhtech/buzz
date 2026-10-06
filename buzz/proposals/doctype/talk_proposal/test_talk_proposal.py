# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, TalkProposalFactory, UserFactory


class TestTalkProposalSpeakerAccess(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.speaker_user = UserFactory.create_once("speaker-perm@example.com").name
		cls.other_user = UserFactory.create_once("other-perm@example.com").name
		cls.manager_user = UserFactory.create_once("manager-perm@example.com").name
		cls.event = create_event_owned_by(cls.manager_user)
		cls.guest_proposal = create_guest_proposal(cls.event, cls.speaker_user)

	def test_speaker_can_read_guest_submitted_proposal(self):
		with self.set_user(self.speaker_user):
			self.assertTrue(frappe.get_doc("Talk Proposal", self.guest_proposal).has_permission("read"))

	def test_speaker_can_write_guest_submitted_proposal(self):
		with self.set_user(self.speaker_user):
			self.assertTrue(frappe.get_doc("Talk Proposal", self.guest_proposal).has_permission("write"))

	def test_speaker_sees_guest_submitted_proposal_in_list(self):
		with self.set_user(self.speaker_user):
			self.assertIn(self.guest_proposal, frappe.get_list("Talk Proposal", pluck="name"))

	def test_non_speaker_cannot_read_or_list_proposal(self):
		with self.set_user(self.other_user):
			proposal = frappe.get_doc("Talk Proposal", self.guest_proposal)
			self.assertFalse(proposal.has_permission("read"))
			self.assertFalse(proposal.has_permission("write"))
			self.assertNotIn(self.guest_proposal, frappe.get_list("Talk Proposal", pluck="name"))

	def test_submitter_sees_proposal_even_without_speaker_row(self):
		proposal = TalkProposalFactory.create(
			event=self.event,
			submitted_by=self.speaker_user,
			speakers=[{"first_name": "Someone", "email": "someone-else@example.com"}],
		)

		with self.set_user(self.speaker_user):
			self.assertIn(proposal.name, frappe.get_list("Talk Proposal", pluck="name"))
			self.assertTrue(proposal.has_permission("read"))

	def test_speaker_email_match_is_case_insensitive(self):
		proposal = create_guest_proposal(self.event, "Mixed-Case@Example.COM")
		user = UserFactory.create_once("mixed-case@example.com").name

		with self.set_user(user):
			doc = frappe.get_doc("Talk Proposal", proposal)
			self.assertTrue(doc.has_permission("read"))
			self.assertTrue(doc.has_permission("write"))
			self.assertIn(proposal, frappe.get_list("Talk Proposal", pluck="name"))

	def test_team_member_sees_their_teams_proposals(self):
		with self.set_user(self.manager_user):
			self.assertIn(self.guest_proposal, frappe.get_list("Talk Proposal", pluck="name"))


class TestCreateTalk(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.speaker_user = UserFactory.create_once("create-talk-speaker@example.com").name
		cls.event = create_event_owned_by(UserFactory.create_once("create-talk-owner@example.com").name)

	def test_create_talk_accepts_the_proposal(self):
		proposal = frappe.get_doc("Talk Proposal", create_guest_proposal(self.event, self.speaker_user))

		talk = proposal.create_talk()

		self.assertEqual(talk.proposal, proposal.name)
		self.assertEqual(frappe.db.get_value("Talk Proposal", proposal.name, "status"), "Accepted")

	def test_speaker_without_an_account_gets_a_website_user(self):
		email = f"new-speaker-{frappe.generate_hash(length=6)}@example.com"
		proposal = frappe.get_doc("Talk Proposal", create_guest_proposal(self.event, email))

		proposal.create_talk()

		self.assertEqual(frappe.db.get_value("User", email, "user_type"), "Website User")

	def test_a_member_of_the_events_team_can_accept_a_proposal(self):
		manager = UserFactory.create_once("create-talk-manager@example.com").name
		event = create_event_owned_by(manager)
		proposal = frappe.get_doc("Talk Proposal", create_guest_proposal(event, self.speaker_user))

		with self.set_user(manager):
			talk = proposal.run_method("create_talk")

		self.assertEqual(talk.proposal, proposal.name)
		self.assertEqual(frappe.db.get_value("Talk Proposal", proposal.name, "status"), "Accepted")

	def test_a_listed_speaker_cannot_accept_their_own_proposal(self):
		# Accepting an earlier talk gives the speaker a profile, so create_talk would reach its
		# end with nothing that needs a permission the speaker lacks.
		frappe.get_doc("Talk Proposal", create_guest_proposal(self.event, self.speaker_user)).create_talk()
		proposal = create_guest_proposal(self.event, self.speaker_user)

		with self.set_user(self.speaker_user):
			# run_doc_method loads the document with a read check and nothing more.
			doc = frappe.get_doc("Talk Proposal", proposal, check_permission=True)
			with self.assertRaises(frappe.PermissionError):
				doc.run_method("create_talk")

		self.assertEqual(frappe.db.get_value("Talk Proposal", proposal, "status"), "Review Pending")
		self.assertEqual(frappe.db.count("Event Talk", {"proposal": proposal}), 0)

	def test_second_create_talk_leaves_no_partial_state(self):
		proposal = frappe.get_doc("Talk Proposal", create_guest_proposal(self.event, self.speaker_user))
		proposal.create_talk()

		proposal.reload()
		with self.assertRaises(frappe.ValidationError):
			proposal.create_talk()

		self.assertEqual(frappe.db.count("Event Talk", {"proposal": proposal.name}), 1)


class TestTalkProposalSpeakerChanges(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.speaker_user = UserFactory.create_once("guard-speaker@example.com").name
		cls.manager_user = UserFactory.create_once("guard-manager@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.manager_user).name
		cls.event = str(BuzzEventFactory.create(team=cls.team).name)

	def test_speaker_edits_an_open_proposal(self):
		doc = self.as_speaker(self.create_proposal())
		doc.title = "Edited by the speaker"
		doc.save()
		self.assertEqual(frappe.db.get_value("Talk Proposal", doc.name, "title"), "Edited by the speaker")

	def test_speaker_withdraws_an_open_proposal(self):
		doc = self.as_speaker(self.create_proposal())
		doc.status = "Withdrawn"
		doc.save()
		self.assertEqual(frappe.db.get_value("Talk Proposal", doc.name, "status"), "Withdrawn")

	def test_speaker_cannot_accept_their_own_proposal(self):
		doc = self.as_speaker(self.create_proposal())
		doc.status = "Accepted"
		self.assertRaises(frappe.PermissionError, doc.save)

	def test_speaker_cannot_edit_an_accepted_proposal(self):
		doc = self.as_speaker(self.create_proposal(status="Accepted"))
		doc.title = "Edited after acceptance"
		self.assertRaises(frappe.PermissionError, doc.save)

	def test_speaker_cannot_edit_after_the_event(self):
		past = str(BuzzEventFactory.create(team=self.team).name)
		frappe.db.set_value(
			"Buzz Event", past, {"start_date": add_days(today(), -10), "end_date": add_days(today(), -9)}
		)
		doc = self.as_speaker(self.create_proposal(event=past))
		doc.title = "Edited after the event"
		self.assertRaises(frappe.PermissionError, doc.save)

	def test_speaker_cannot_move_a_proposal_to_another_event(self):
		other = BuzzEventFactory.create(team=self.team).name
		doc = self.as_speaker(self.create_proposal())
		doc.event = other
		self.assertRaises(frappe.CannotChangeConstantError, doc.save)

	def test_speaker_cannot_move_a_proposal_into_an_event_they_run(self):
		own_event = create_event_owned_by(self.speaker_user)
		doc = self.as_speaker(self.create_proposal())
		doc.event = own_event
		doc.status = "Accepted"
		self.assertRaises(frappe.CannotChangeConstantError, doc.save)

	def test_the_team_cannot_move_a_proposal_to_another_event(self):
		other = BuzzEventFactory.create(team=self.team).name
		name = self.create_proposal()
		with self.set_user(self.manager_user):
			doc = frappe.get_doc("Talk Proposal", name)
			doc.event = other
			self.assertRaises(frappe.CannotChangeConstantError, doc.save)

	def test_a_proposal_cannot_lose_its_event(self):
		doc = self.as_speaker(self.create_proposal())
		doc.event = None
		self.assertRaises(frappe.CannotChangeConstantError, doc.save)

	def test_speaker_cannot_remove_themselves(self):
		doc = self.as_speaker(self.create_proposal())
		doc.speakers = []
		self.assertRaises(frappe.PermissionError, doc.save)

	def test_speaker_adds_a_co_speaker(self):
		doc = self.as_speaker(self.create_proposal())
		doc.append("speakers", {"first_name": "Co", "email": "guard-co@example.com"})
		doc.save()
		self.assertEqual(len(frappe.get_doc("Talk Proposal", doc.name).speakers), 2)

	def test_the_team_still_accepts_a_proposal(self):
		name = self.create_proposal()
		with self.set_user(self.manager_user):
			doc = frappe.get_doc("Talk Proposal", name)
			doc.status = "Accepted"
			doc.save()
		self.assertEqual(frappe.db.get_value("Talk Proposal", name, "status"), "Accepted")

	def create_proposal(self, event: str | None = None, status: str = "Review Pending") -> str:
		name = create_guest_proposal(event or self.event, self.speaker_user)
		if status != "Review Pending":
			frappe.db.set_value("Talk Proposal", name, "status", status)
		return name

	def as_speaker(self, name: str):
		"""The speaker stays signed in until the test ends."""
		self.enterContext(self.set_user(self.speaker_user))
		return frappe.get_doc("Talk Proposal", name)


def create_event_owned_by(user: str) -> str:
	return str(BuzzEventFactory.create(team=BuzzTeamFactory.create_owned_by(user).name).name)


def create_guest_proposal(event: str, speaker_email: str, **values) -> str:
	"""The public form's submission: `owner` and `submitted_by` are both Guest."""
	with IntegrationTestCase.set_user("Guest"):
		proposal = TalkProposalFactory.create(
			"guest_submitted",
			event=event,
			speakers=[{"first_name": "Speaker", "email": speaker_email}],
			flags={"ignore_permissions": True},
			**values,
		)
	return proposal.name


def make_guest_proposal(event: str, speaker_email: str, title: str | None = None) -> str:
	"""Kept for `test_communications` until the cleanup PR; new tests use the factory."""
	return create_guest_proposal(event, speaker_email, **({"title": title} if title else {}))
