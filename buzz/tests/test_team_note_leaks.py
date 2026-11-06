import frappe
from frappe.desk.form.activity import get_activity_timeline
from frappe.desk.form.load import getdoc

from buzz.tests.base_test_cases import TeamPermissionTestCase
from buzz.tests.factories import (
	BuzzTeamMembershipFactory,
	CommentFactory,
	TalkProposalFactory,
	UserFactory,
)

SPEAKER = "note-leak-speaker@example.com"
NOTE = "Internal: weak abstract"


class TestTeamNoteLeaks(TeamPermissionTestCase):
	"""A speaker reads their own proposal, but not the team's notes on it."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.speaker = UserFactory.create_once(SPEAKER)
		cls.speaker.add_roles("Buzz User")
		cls.viewer = UserFactory.create_once("note-leak-viewer@example.com").name
		BuzzTeamMembershipFactory.create(team=cls.team_a, user=cls.viewer, team_role="Viewer")

	def setUp(self):
		super().setUp()
		self.proposal = TalkProposalFactory.create(
			event=self.event_a, speakers=[{"first_name": "Speaker", "email": SPEAKER}]
		).name
		CommentFactory.create(reference_name=self.proposal, content=f"<p>{NOTE}</p>")
		CommentFactory.create(comment_type="Info", reference_name=self.proposal, content="Status changed")

	def timeline_as(self, user: str) -> str:
		with self.set_user(user):
			return frappe.as_json(get_activity_timeline("Talk Proposal", self.proposal))

	def docinfo_as(self, user: str) -> str:
		with self.set_user(user):
			getdoc("Talk Proposal", self.proposal)
			return frappe.as_json(frappe.response.pop("docinfo"))

	def test_speaker_still_reads_the_proposal(self):
		self.assertTrue(self.has_permission_as(SPEAKER, "read", "Talk Proposal", self.proposal))

	def test_speaker_does_not_get_notes_from_the_desk_endpoints(self):
		self.assertNotIn(NOTE, self.timeline_as(SPEAKER))
		self.assertNotIn(NOTE, self.docinfo_as(SPEAKER))

	def test_speaker_keeps_activity_logs(self):
		self.assertIn("Status changed", self.timeline_as(SPEAKER))

	def test_members_get_notes(self):
		for user in (self.alice, self.viewer):
			self.assertIn(NOTE, self.timeline_as(user))
			self.assertIn(NOTE, self.docinfo_as(user))
