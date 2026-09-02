# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.forms.test_forms import ensure_prompt_named_record
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team

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


def make_test_event(category: str, host: str, team: str | None = None) -> str:
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
			"team": team,
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
		cls.speaker_user = make_test_user("speaker-perm@example.com")
		cls.other_user = make_test_user("other-perm@example.com")
		cls.manager_user = make_test_user("manager-perm@example.com", roles=["Event Manager"])
		cls.team = create_owned_team("Proposal Perm Team", cls.manager_user)
		cls.event = make_test_event(cls.category, cls.host, team=cls.team)
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

	def test_speaker_email_match_is_case_insensitive(self):
		proposal = make_guest_proposal(self.event, "Mixed-Case@Example.COM")
		user = make_test_user("mixed-case@example.com")

		frappe.set_user(user)
		doc = frappe.get_doc("Talk Proposal", proposal)
		self.assertTrue(doc.has_permission("read"))
		self.assertTrue(doc.has_permission("write"))
		self.assertIn(proposal, frappe.get_list("Talk Proposal", pluck="name"))

	def test_team_member_sees_their_teams_proposals(self):
		frappe.set_user(self.manager_user)
		self.assertIn(self.guest_proposal, frappe.get_list("Talk Proposal", pluck="name"))


class TestCreateTalk(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.category = ensure_prompt_named_record("Event Category", "Proposal Perm Category")
		cls.host = ensure_prompt_named_record("Event Host", "Proposal Perm Host")
		cls.speaker_user = make_test_user("create-talk-speaker@example.com")
		cls.owner_user = make_test_user("create-talk-owner@example.com", roles=["Event Manager"])
		cls.event = make_test_event(
			cls.category, cls.host, team=create_owned_team("Create Talk Owner Team", cls.owner_user)
		)

	def test_create_talk_accepts_the_proposal(self):
		proposal = frappe.get_doc("Talk Proposal", make_guest_proposal(self.event, self.speaker_user))

		talk = proposal.create_talk()

		self.assertEqual(talk.proposal, proposal.name)
		self.assertEqual(frappe.db.get_value("Talk Proposal", proposal.name, "status"), "Accepted")

	def test_speaker_without_an_account_gets_a_website_user(self):
		email = f"new-speaker-{frappe.generate_hash(length=6)}@example.com"
		proposal = frappe.get_doc("Talk Proposal", make_guest_proposal(self.event, email))

		proposal.create_talk()

		self.assertEqual(frappe.db.get_value("User", email, "user_type"), "Website User")

	def test_a_member_of_the_events_team_can_accept_a_proposal(self):
		manager = make_test_user("create-talk-manager@example.com", roles=["Event Manager"])
		team = create_owned_team("Create Talk Team", manager)
		event = make_test_event(self.category, self.host, team=team)
		proposal = frappe.get_doc("Talk Proposal", make_guest_proposal(event, self.speaker_user))

		frappe.set_user(manager)
		self.addCleanup(frappe.set_user, "Administrator")
		talk = proposal.run_method("create_talk")

		self.assertEqual(talk.proposal, proposal.name)
		self.assertEqual(frappe.db.get_value("Talk Proposal", proposal.name, "status"), "Accepted")

	def test_a_listed_speaker_cannot_accept_their_own_proposal(self):
		# A speaker who already has a profile reaches the end of create_talk: nothing it
		# touches needs a permission the speaker lacks.
		if not frappe.db.exists("Speaker Profile", {"user": self.speaker_user}):
			frappe.get_doc({"doctype": "Speaker Profile", "user": self.speaker_user}).insert()
		proposal = frappe.get_doc("Talk Proposal", make_guest_proposal(self.event, self.speaker_user))

		frappe.set_user(self.speaker_user)
		self.addCleanup(frappe.set_user, "Administrator")
		# run_doc_method loads the document with a read check and nothing more.
		doc = frappe.get_doc("Talk Proposal", proposal.name, check_permission=True)

		with self.assertRaises(frappe.PermissionError):
			doc.run_method("create_talk")

		self.assertEqual(frappe.db.get_value("Talk Proposal", proposal.name, "status"), "Review Pending")
		self.assertEqual(frappe.db.count("Event Talk", {"proposal": proposal.name}), 0)

	def test_second_create_talk_leaves_no_partial_state(self):
		proposal = frappe.get_doc("Talk Proposal", make_guest_proposal(self.event, self.speaker_user))
		proposal.create_talk()

		proposal.reload()
		with self.assertRaises(frappe.ValidationError):
			proposal.create_talk()

		self.assertEqual(frappe.db.count("Event Talk", {"proposal": proposal.name}), 1)


class TestTalkProposalSpeakerChanges(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.category = ensure_prompt_named_record("Event Category", "Proposal Perm Category")
		cls.host = ensure_prompt_named_record("Event Host", "Proposal Perm Host")
		cls.speaker_user = make_test_user("guard-speaker@example.com")
		cls.manager_user = make_test_user("guard-manager@example.com", roles=["Event Manager"])
		cls.team = create_owned_team("Proposal Guard Team", cls.manager_user)
		cls.event = make_test_event(cls.category, cls.host, team=cls.team)

	def tearDown(self):
		frappe.set_user("Administrator")

	def proposal(self, event: str | None = None, status: str = "Review Pending") -> str:
		name = make_guest_proposal(event or self.event, self.speaker_user)
		if status != "Review Pending":
			frappe.db.set_value("Talk Proposal", name, "status", status)
		return name

	def as_speaker(self, name: str):
		frappe.set_user(self.speaker_user)
		return frappe.get_doc("Talk Proposal", name)

	def test_speaker_edits_an_open_proposal(self):
		doc = self.as_speaker(self.proposal())
		doc.title = "Edited by the speaker"
		doc.save()
		self.assertEqual(frappe.db.get_value("Talk Proposal", doc.name, "title"), "Edited by the speaker")

	def test_speaker_withdraws_an_open_proposal(self):
		doc = self.as_speaker(self.proposal())
		doc.status = "Withdrawn"
		doc.save()
		self.assertEqual(frappe.db.get_value("Talk Proposal", doc.name, "status"), "Withdrawn")

	def test_speaker_cannot_accept_their_own_proposal(self):
		doc = self.as_speaker(self.proposal())
		doc.status = "Accepted"
		self.assertRaises(frappe.PermissionError, doc.save)

	def test_speaker_cannot_edit_an_accepted_proposal(self):
		doc = self.as_speaker(self.proposal(status="Accepted"))
		doc.title = "Edited after acceptance"
		self.assertRaises(frappe.PermissionError, doc.save)

	def test_speaker_cannot_edit_after_the_event(self):
		past = make_test_event(self.category, self.host, team=self.team)
		frappe.db.set_value("Buzz Event", past, {"start_date": "2020-01-01", "end_date": "2020-01-02"})
		doc = self.as_speaker(self.proposal(event=past))
		doc.title = "Edited after the event"
		self.assertRaises(frappe.PermissionError, doc.save)

	def test_speaker_cannot_move_a_proposal_to_another_event(self):
		other = make_test_event(self.category, self.host, team=self.team)
		doc = self.as_speaker(self.proposal())
		doc.event = other
		self.assertRaises(frappe.CannotChangeConstantError, doc.save)

	def test_speaker_cannot_move_a_proposal_into_an_event_they_run(self):
		own_team = create_owned_team("Proposal Speaker Own Team", self.speaker_user)
		own_event = make_test_event(self.category, self.host, team=own_team)
		doc = self.as_speaker(self.proposal())
		doc.event = own_event
		doc.status = "Accepted"
		self.assertRaises(frappe.CannotChangeConstantError, doc.save)

	def test_the_team_cannot_move_a_proposal_to_another_event(self):
		other = make_test_event(self.category, self.host, team=self.team)
		name = self.proposal()
		frappe.set_user(self.manager_user)
		doc = frappe.get_doc("Talk Proposal", name)
		doc.event = other
		self.assertRaises(frappe.CannotChangeConstantError, doc.save)

	def test_a_proposal_cannot_lose_its_event(self):
		doc = self.as_speaker(self.proposal())
		doc.event = None
		self.assertRaises(frappe.CannotChangeConstantError, doc.save)

	def test_speaker_cannot_remove_themselves(self):
		doc = self.as_speaker(self.proposal())
		doc.speakers = []
		self.assertRaises(frappe.PermissionError, doc.save)

	def test_speaker_adds_a_co_speaker(self):
		doc = self.as_speaker(self.proposal())
		doc.append("speakers", {"first_name": "Co", "email": "guard-co@example.com"})
		doc.save()
		self.assertEqual(len(frappe.get_doc("Talk Proposal", doc.name).speakers), 2)

	def test_the_team_still_accepts_a_proposal(self):
		name = self.proposal()
		frappe.set_user(self.manager_user)
		doc = frappe.get_doc("Talk Proposal", name)
		doc.status = "Accepted"
		doc.save()
		self.assertEqual(frappe.db.get_value("Talk Proposal", name, "status"), "Accepted")
