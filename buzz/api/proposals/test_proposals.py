import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils.data import cstr, getdate
from frappe.utils.response import json_handler

from buzz.api.events.exceptions import CannotManageEvent, EventNotFound
from buzz.api.forms.test_forms import ensure_prompt_named_record
from buzz.api.proposals import (
	accept_proposal,
	get_event_proposal_trend,
	get_event_proposals,
	get_my_proposals,
)
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team
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
				"start_time",
				"end_date",
				"venue",
				"banner_image",
				"allow_editing_talks_after_acceptance",
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


class TestGetEventProposals(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.category = ensure_prompt_named_record("Event Category", "Event Proposals Category")
		cls.host = ensure_prompt_named_record("Event Host", "Event Proposals Host")
		cls.manager = make_test_user("proposals-manager@example.com")
		cls.outsider = make_test_user("proposals-outsider@example.com")
		cls.team = create_owned_team(f"Proposals Team {frappe.generate_hash(length=6)}", cls.manager)
		cls.event = cstr(make_test_event(cls.category, cls.host, team=cls.team))
		cls.other_event = cstr(make_test_event(cls.category, cls.host, team=cls.team))
		cls.pending = make_guest_proposal(cls.event, "one@example.com", title="Pending Kubernetes")
		cls.accepted = make_guest_proposal(cls.event, "two@example.com", title="Accepted Rust")
		frappe.db.set_value("Talk Proposal", cls.accepted, "status", "Accepted")
		cls.elsewhere = make_guest_proposal(cls.other_event, "three@example.com")

	def tearDown(self):
		frappe.set_user("Administrator")

	def listed(self, **kwargs) -> list[str]:
		frappe.set_user(self.manager)
		response = get_event_proposals(self.event, **kwargs)
		return [proposal.name for proposal in response.proposals]

	def test_lists_only_this_events_proposals(self):
		names = self.listed()
		self.assertIn(self.pending, names)
		self.assertIn(self.accepted, names)
		self.assertNotIn(self.elsewhere, names)

	def test_lists_proposals_the_manager_is_not_a_speaker_on(self):
		"""The team reads its whole pipeline, not just the talks it happens to be on."""
		frappe.set_user(self.manager)
		self.assertEqual(get_event_proposals(self.event).total, 2)

	def test_outsider_cannot_read_the_pipeline(self):
		frappe.set_user(self.outsider)
		with self.assertRaises(CannotManageEvent):
			get_event_proposals(self.event)

	def test_unknown_event_is_not_found(self):
		frappe.set_user(self.manager)
		with self.assertRaises(EventNotFound):
			get_event_proposals("does-not-exist")

	def test_status_filter_narrows_the_page(self):
		self.assertEqual(self.listed(statuses="Accepted"), [self.accepted])

	def test_search_matches_the_title(self):
		self.assertEqual(self.listed(search="Kubernetes"), [self.pending])

	def test_search_matches_a_speaker_email(self):
		self.assertEqual(self.listed(search="two@example.com"), [self.accepted])

	def test_search_that_matches_nothing_returns_nothing(self):
		self.assertEqual(self.listed(search="Fortran"), [])

	def test_matched_counts_the_filter_while_total_counts_the_event(self):
		frappe.set_user(self.manager)
		response = get_event_proposals(self.event, statuses="Accepted")
		self.assertEqual(response.matched, 1)
		self.assertEqual(response.total, 2)

	def test_page_reports_whether_more_are_waiting(self):
		frappe.set_user(self.manager)
		first = get_event_proposals(self.event, limit=1)
		self.assertTrue(first.has_next_page)
		self.assertFalse(get_event_proposals(self.event, start=1, limit=1).has_next_page)

	def test_order_reverses_the_page(self):
		self.assertEqual(list(reversed(self.listed())), self.listed(order="asc"))

	def test_rows_carry_their_speakers(self):
		frappe.set_user(self.manager)
		row = next(p for p in get_event_proposals(self.event).proposals if p.name == self.pending)
		self.assertEqual([speaker.email for speaker in row.speakers], ["one@example.com"])

	def test_a_writer_is_told_they_may_change_a_status(self):
		frappe.set_user(self.manager)
		self.assertTrue(get_event_proposals(self.event).can_write)

	def test_a_read_only_member_reads_the_pipeline_without_the_write_flag(self):
		"""Viewer and Frontdesk pass the read check the list uses and fail the write one."""
		viewer = make_test_user("proposals-viewer@example.com")
		frappe.get_doc(
			{
				"doctype": "Buzz Team Membership",
				"team": self.team,
				"user": viewer,
				"team_role": "Viewer",
				"enabled": 1,
			}
		).insert(ignore_permissions=True)

		frappe.set_user(viewer)
		response = get_event_proposals(self.event)
		self.assertEqual(response.total, 2)
		self.assertFalse(response.can_write)


class TestGetEventProposalTrend(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.category = ensure_prompt_named_record("Event Category", "Proposal Trend Category")
		cls.host = ensure_prompt_named_record("Event Host", "Proposal Trend Host")
		cls.manager = make_test_user("trend-manager@example.com")
		cls.outsider = make_test_user("trend-outsider@example.com")
		cls.team = create_owned_team(f"Trend Team {frappe.generate_hash(length=6)}", cls.manager)
		cls.event = cstr(make_test_event(cls.category, cls.host, team=cls.team))
		cls.proposal = make_guest_proposal(cls.event, "trend@example.com")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_window_is_zero_filled_and_ends_today(self):
		frappe.set_user(self.manager)
		trend = get_event_proposal_trend(self.event, days=7)
		self.assertEqual(len(trend.per_day), 7)
		self.assertEqual(trend.per_day[-1].date, getdate())
		self.assertEqual(trend.per_day[-1].count, 1)

	def test_total_and_status_split_agree(self):
		frappe.set_user(self.manager)
		trend = get_event_proposal_trend(self.event)
		self.assertEqual(trend.total, 1)
		self.assertEqual(sum(row.count for row in trend.by_status), trend.total)

	def test_days_are_clamped_to_a_sane_window(self):
		frappe.set_user(self.manager)
		self.assertEqual(len(get_event_proposal_trend(self.event, days=500).per_day), 90)
		self.assertEqual(len(get_event_proposal_trend(self.event, days=0).per_day), 2)

	def test_outsider_cannot_read_the_trend(self):
		frappe.set_user(self.outsider)
		with self.assertRaises(CannotManageEvent):
			get_event_proposal_trend(self.event)


class TestAcceptProposal(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.category = ensure_prompt_named_record("Event Category", "Accept Proposal Category")
		cls.host = ensure_prompt_named_record("Event Host", "Accept Proposal Host")
		cls.manager = make_test_user("accept-manager@example.com")
		cls.outsider = make_test_user("accept-outsider@example.com")
		cls.team = create_owned_team(f"Accept Team {frappe.generate_hash(length=6)}", cls.manager)
		cls.event = cstr(make_test_event(cls.category, cls.host, team=cls.team))

	def setUp(self):
		self.proposal = make_guest_proposal(self.event, "accept-speaker@example.com")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_accepting_creates_the_talk_and_sets_the_status(self):
		frappe.set_user(self.manager)
		accepted = accept_proposal(self.proposal)

		self.assertEqual(accepted.status, "Accepted")
		self.assertEqual(frappe.db.get_value("Talk Proposal", self.proposal, "status"), "Accepted")
		self.assertEqual(frappe.db.get_value("Event Talk", accepted.talk, "proposal"), self.proposal)

	def test_the_talk_carries_the_proposal_speakers(self):
		frappe.set_user(self.manager)
		talk = frappe.get_doc("Event Talk", accept_proposal(self.proposal).talk)
		self.assertEqual(len(talk.speakers), 1)

	def test_accepting_twice_reuses_the_talk_rather_than_duplicating_it(self):
		"""A reviewer can move a proposal off Accepted and back; the programme has one entry."""
		frappe.set_user(self.manager)
		first = accept_proposal(self.proposal)
		frappe.db.set_value("Talk Proposal", self.proposal, "status", "Shortlisted")

		second = accept_proposal(self.proposal)
		self.assertEqual(second.talk, first.talk)
		self.assertEqual(second.status, "Accepted")
		self.assertEqual(frappe.db.count("Event Talk", {"proposal": self.proposal}), 1)

	def test_a_speaker_cannot_accept_their_own_proposal(self):
		"""A listed speaker holds write on the document; accepting is the team's call."""
		speaker = make_test_user("accept-speaker@example.com")
		frappe.set_user(speaker)
		with self.assertRaises(frappe.PermissionError):
			accept_proposal(self.proposal)

	def test_an_outsider_cannot_accept(self):
		frappe.set_user(self.outsider)
		with self.assertRaises(frappe.PermissionError):
			accept_proposal(self.proposal)
