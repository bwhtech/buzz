from buzz.api.comments import add_comment
from buzz.api.notifications import get_notifications, mark_as_read
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

	def groups_as(self, user: str) -> list:
		with self.set_user(user):
			return get_notifications()

	def test_groups_notes_and_replies_by_talk_newest_first(self):
		self.comment_as(self.manager, self.first, "<p>Push for the <b>main hall</b></p>")
		self.comment_as(self.manager, self.second, "<p>Overlaps with the sync talk?</p>")
		CommunicationFactory.create(
			reference_name=self.first,
			sender=SPEAKER,
			sender_full_name="Meera Krishnan",
			content="<p>Slides attached</p>",
		)

		groups = self.groups_as(self.alice)

		self.assertEqual([group.reference_name for group in groups], [self.first, self.second])
		first = groups[0]
		self.assertEqual(first.title, "Scaling Postgres")
		self.assertTrue(first.subscribed)
		reply, note = first.notifications
		self.assertEqual(
			(reply.kind, reply.actor, reply.snippet), ("reply", "Meera Krishnan", "Slides attached")
		)
		self.assertEqual((note.kind, note.snippet), ("comment", "Push for the main hall"))
		# The manager commented, so only the speaker's reply reaches them.
		[manager_group] = self.groups_as(self.manager)
		self.assertEqual([entry.kind for entry in manager_group.notifications], ["reply"])

	def test_mark_as_read_clears_one_talk_for_the_session_user(self):
		self.comment_as(self.manager, self.first, "<p>One</p>")
		self.comment_as(self.manager, self.second, "<p>Two</p>")

		with self.set_user(self.alice):
			mark_as_read("Talk Proposal", self.first)

		read = {
			group.reference_name: [entry.read for entry in group.notifications]
			for group in self.groups_as(self.alice)
			if group.reference_name in (self.first, self.second)
		}
		self.assertEqual(read, {self.first: [True], self.second: [False]})
