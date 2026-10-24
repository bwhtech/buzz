from buzz.api.comments import add_comment
from buzz.api.notifications import get_notifications, mark_all_as_read, mark_as_read
from buzz.subscriptions import Subscriptions
from buzz.tests.base_test_cases import TeamPermissionTestCase
from buzz.tests.factories import (
	BuzzTeamMembershipFactory,
	CommunicationFactory,
	TalkProposalFactory,
	UserFactory,
)
from buzz.tests.utils import mute_outgoing_email

SPEAKER = "notifications-speaker@example.com"


class TestNotifications(TeamPermissionTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.manager = UserFactory.create_once("notifications-manager@example.com").name
		BuzzTeamMembershipFactory.create(team=cls.team_a, user=cls.manager, team_role="Manager")

	def setUp(self):
		super().setUp()
		mute_outgoing_email(self)
		self.first = self.proposal("Scaling Postgres")
		self.second = self.proposal("Offline-first apps")
		for proposal in (self.first, self.second):
			Subscriptions("Talk Proposal", proposal).subscribe(self.alice)

	def proposal(self, title: str) -> str:
		return TalkProposalFactory.create(
			event=self.event_a, title=title, speakers=[{"first_name": "Speaker", "email": SPEAKER}]
		).name

	def comment_as(self, user: str, proposal: str, content: str) -> None:
		with self.set_user(user):
			add_comment("Talk Proposal", proposal, content)

	def notifications_as(self, user: str) -> list:
		proposals = (self.first, self.second)
		with self.set_user(user):
			return [entry for entry in get_notifications() if entry.reference_name in proposals]

	def test_lists_notes_and_replies_newest_first_with_their_talk(self):
		self.comment_as(self.manager, self.first, "<p>Push for the <b>main hall</b></p>")
		CommunicationFactory.create(
			reference_name=self.second,
			sender=SPEAKER,
			sender_full_name="Meera Krishnan",
			content="<p>Slides attached</p>",
		)

		reply, note = self.notifications_as(self.alice)

		self.assertEqual(
			(reply.kind, reply.actor, reply.snippet, reply.title),
			("reply", "Meera Krishnan", "Slides attached", "Offline-first apps"),
		)
		self.assertEqual(
			(note.kind, note.snippet, note.title), ("comment", "Push for the main hall", "Scaling Postgres")
		)
		self.assertFalse(note.read)

	def test_marks_one_or_all_as_read_for_the_session_user_only(self):
		self.comment_as(self.manager, self.first, "<p>One</p>")
		self.comment_as(self.manager, self.second, "<p>Two</p>")
		Subscriptions("Talk Proposal", self.first).subscribe(self.bob)
		self.comment_as(self.manager, self.first, "<p>Three</p>")

		with self.set_user(self.alice):
			mark_as_read(self.notifications_as(self.alice)[-1].name)
		self.assertEqual([entry.read for entry in self.notifications_as(self.alice)], [False, False, True])

		with self.set_user(self.alice):
			mark_all_as_read()
		self.assertTrue(all(entry.read for entry in self.notifications_as(self.alice)))
		self.assertEqual([entry.read for entry in self.notifications_as(self.bob)], [False])
