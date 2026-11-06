import frappe

from buzz.api.events.exceptions import CannotManageEvent
from buzz.api.search import get_palette_events, search_event
from buzz.api.search.exceptions import UnknownSearchSection
from buzz.permissions import SECTIONS
from buzz.tests.base_test_cases import TeamPermissionTestCase
from buzz.tests.factories import (
	BuzzEventCollaboratorFactory,
	BuzzEventFactory,
	EventTicketFactory,
	TalkProposalFactory,
)

TERM = "zorblax"


def palette_as(test, user: str) -> dict:
	with test.set_user(user):
		return {event.name: event for event in get_palette_events().events}


class TestPaletteEvents(TeamPermissionTestCase):
	def test_team_member_sees_own_team_events_with_edit_everywhere(self):
		events = palette_as(self, self.alice)

		self.assertIn(str(self.event_a), events)
		self.assertNotIn(str(self.event_b), events)
		self.assertEqual(events[str(self.event_a)].access, dict.fromkeys(SECTIONS, "Edit"))
		self.assertEqual(events[str(self.event_a)].team_title, "Perm Team A")

	def test_outsider_sees_no_team_events(self):
		events = palette_as(self, self.outsider)

		self.assertFalse({str(self.event_a), str(self.event_b)} & set(events))

	def test_collaborator_sees_only_the_sections_granted(self):
		collaborator = BuzzEventCollaboratorFactory.create(
			"accepted", event=self.event_a, talks_access="View", guests_access=None
		)

		access = palette_as(self, collaborator.user)[str(self.event_a)].access

		self.assertEqual(access, {**dict.fromkeys(SECTIONS), "details": "View", "talks": "View"})


class TestSearchEvent(TeamPermissionTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.collaborator = BuzzEventCollaboratorFactory.create(
			"accepted", event=cls.event_a, talks_access="View", guests_access=None
		).user

	def setUp(self):
		super().setUp()
		EventTicketFactory.create("submitted", event=self.event_a, first_name=TERM)
		TalkProposalFactory.create(event=self.event_a, title=f"{TERM} talk")

	def search(self, user: str, event=None, term: str = TERM, section: str | None = None):
		with self.set_user(user):
			return search_event(str(event or self.event_a), term, section)

	def keys(self, response) -> list[str]:
		return [group.key for group in response.groups]

	def test_team_member_gets_every_matching_group(self):
		self.assertEqual(self.keys(self.search(self.alice)), ["guests", "talks"])

	def test_outsider_cannot_search(self):
		with self.assertRaises(CannotManageEvent):
			self.search(self.outsider)

	def test_collaborator_gets_only_readable_sections(self):
		self.assertEqual(self.keys(self.search(self.collaborator)), ["talks"])

	def test_section_filter_narrows_and_validates(self):
		self.assertEqual(self.keys(self.search(self.alice, section="talks")), ["talks"])
		with self.assertRaises(UnknownSearchSection):
			self.search(self.alice, section="nowhere")

	def test_other_events_records_are_excluded(self):
		TalkProposalFactory.create(event=self.event_a2, title=f"{TERM} elsewhere")

		talks = self.search(self.alice, section="talks").groups[0].records

		self.assertNotIn(f"{TERM} elsewhere", [record.title for record in talks])

	def test_one_character_term_returns_nothing(self):
		self.assertEqual(self.search(self.alice, term=" z ").groups, [])

	def test_group_holds_at_most_three_records(self):
		for _ in range(4):
			TalkProposalFactory.create(event=self.event_a, title=f"{TERM} more")

		self.assertEqual(len(self.search(self.alice, section="talks").groups[0].records), 3)
