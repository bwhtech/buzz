import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils.data import getdate

from buzz.api.events.exceptions import CannotManageEvent, EventNotFound
from buzz.api.proposals import get_event_proposal_trend, get_event_proposals, set_proposal_state
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	BuzzTeamMembershipFactory,
	TalkProposalFactory,
	UserFactory,
)

ACCEPTED = '[["status", "in", ["Accepted"]]]'


class TestGetEventProposals(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.manager = UserFactory.create_once("proposals-manager@example.com").name
		cls.outsider = UserFactory.create_once("proposals-outsider@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.manager).name
		cls.event = str(BuzzEventFactory.create(team=cls.team).name)
		cls.other_event = str(BuzzEventFactory.create(team=cls.team).name)
		cls.pending = create_guest_proposal(cls.event, "one@example.com", title="Pending Kubernetes")
		cls.accepted = create_guest_proposal(cls.event, "two@example.com", title="Accepted Rust")
		frappe.db.set_value("Talk Proposal", cls.accepted, "status", "Accepted")
		cls.elsewhere = create_guest_proposal(cls.other_event, "three@example.com", title="Elsewhere Go")

	def test_lists_only_this_events_proposals(self):
		names = self.listed()
		self.assertIn(self.pending, names)
		self.assertIn(self.accepted, names)
		self.assertNotIn(self.elsewhere, names)

	def test_lists_proposals_the_manager_is_not_a_speaker_on(self):
		# The team reads its whole pipeline, not just the talks it happens to be on.
		self.assertEqual(self.as_manager().total, 2)

	def test_outsider_cannot_read_the_pipeline(self):
		with self.set_user(self.outsider), self.assertRaises(CannotManageEvent):
			get_event_proposals(self.event)

	def test_unknown_event_is_not_found(self):
		with self.set_user(self.manager), self.assertRaises(EventNotFound):
			get_event_proposals("does-not-exist")

	def test_status_filter_narrows_the_page(self):
		self.assertEqual(self.listed(filters=ACCEPTED), [self.accepted])

	def test_search_matches_the_title(self):
		self.assertEqual(self.listed(search="Kubernetes"), [self.pending])

	def test_search_matches_a_speaker_email(self):
		self.assertEqual(self.listed(search="two@example.com"), [self.accepted])

	def test_search_that_matches_nothing_returns_nothing(self):
		self.assertEqual(self.listed(search="Fortran"), [])

	def test_matched_counts_the_filter_while_total_counts_the_event(self):
		response = self.as_manager(filters=ACCEPTED)
		self.assertEqual(response.matched, 1)
		self.assertEqual(response.total, 2)

	def test_page_reports_whether_more_are_waiting(self):
		self.assertTrue(self.as_manager(limit=1).has_next_page)
		self.assertFalse(self.as_manager(start=1, limit=1).has_next_page)

	def test_order_reverses_the_page(self):
		self.assertEqual(list(reversed(self.listed())), self.listed(order="asc"))

	def test_rows_carry_their_speakers(self):
		row = next(p for p in self.as_manager().proposals if p.name == self.pending)
		self.assertEqual([speaker.email for speaker in row.speakers], ["one@example.com"])

	def test_a_writer_is_told_they_may_change_a_status(self):
		self.assertTrue(self.as_manager().can_write)

	def test_a_read_only_member_reads_the_pipeline_without_the_write_flag(self):
		# Viewer and Frontdesk pass the read check the list uses and fail the write one.
		viewer = UserFactory.create_once("proposals-viewer@example.com").name
		BuzzTeamMembershipFactory.create(team=self.team, user=viewer, team_role="Viewer")

		with self.set_user(viewer):
			response = get_event_proposals(self.event)

		self.assertEqual(response.total, 2)
		self.assertFalse(response.can_write)

	def as_manager(self, **kwargs):
		with self.set_user(self.manager):
			return get_event_proposals(self.event, **kwargs)

	def listed(self, **kwargs) -> list[str]:
		return [proposal.name for proposal in self.as_manager(**kwargs).proposals]


class TestGetEventProposalTrend(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.manager = UserFactory.create_once("trend-manager@example.com").name
		cls.outsider = UserFactory.create_once("trend-outsider@example.com").name
		team = BuzzTeamFactory.create_owned_by(cls.manager).name
		cls.event = str(BuzzEventFactory.create(team=team).name)
		cls.proposal = create_guest_proposal(cls.event, "trend@example.com")

	def setUp(self):
		self.enterContext(self.set_user(self.manager))

	def test_window_is_zero_filled_and_ends_today(self):
		trend = get_event_proposal_trend(self.event, days=7)
		self.assertEqual(len(trend.per_day), 7)
		self.assertEqual(trend.per_day[-1].date, getdate())
		self.assertEqual(trend.per_day[-1].count, 1)

	def test_total_and_status_split_agree(self):
		trend = get_event_proposal_trend(self.event)
		self.assertEqual(trend.total, 1)
		self.assertEqual(sum(row.count for row in trend.by_status), trend.total)

	def test_days_are_clamped_to_a_sane_window(self):
		self.assertEqual(len(get_event_proposal_trend(self.event, days=500).per_day), 90)
		self.assertEqual(len(get_event_proposal_trend(self.event, days=0).per_day), 2)

	def test_outsider_cannot_read_the_trend(self):
		with self.set_user(self.outsider), self.assertRaises(CannotManageEvent):
			get_event_proposal_trend(self.event)


class TestSetProposalState(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.manager = UserFactory.create_once("proposal-state-manager@example.com").name
		cls.outsider = UserFactory.create_once("proposal-state-outsider@example.com").name
		team = BuzzTeamFactory.create_owned_by(cls.manager).name
		cls.event = str(BuzzEventFactory.create(team=team).name)

	def setUp(self):
		self.enterContext(self.set_user(self.manager))

	def test_closing_then_opening_round_trips(self):
		self.assertTrue(set_proposal_state(self.event, closed=True).proposals_closed)
		self.assertTrue(get_event_proposals(self.event).proposals_closed)

		self.assertFalse(set_proposal_state(self.event, closed=False).proposals_closed)
		self.assertFalse(get_event_proposals(self.event).proposals_closed)

	def test_opening_publishes_a_form_that_was_never_published(self):
		self.unpublish_the_proposal_form()

		self.assertFalse(set_proposal_state(self.event, closed=False).proposals_closed)

	def test_an_unpublished_form_reads_as_closed(self):
		self.unpublish_the_proposal_form()

		self.assertTrue(get_event_proposals(self.event).proposals_closed)

	def test_the_link_points_at_the_events_own_form_page(self):
		route = frappe.db.get_value("Buzz Event", self.event, "route")
		self.assertEqual(get_event_proposals(self.event).proposal_link, f"/b/{route}/propose-talk")

	def test_an_outsider_cannot_change_the_state(self):
		with self.set_user(self.outsider), self.assertRaises(CannotManageEvent):
			set_proposal_state(self.event, closed=True)

	def unpublish_the_proposal_form(self):
		event = frappe.get_doc("Buzz Event", self.event)
		for row in event.custom_forms:
			if row.form_doctype == "Talk Proposal":
				row.publish = 0
		event.save(ignore_permissions=True)


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
