import frappe

from buzz.api.comments import add_comment, get_subscription, set_subscription
from buzz.api.comments.exceptions import NotTeamMember
from buzz.api.teams.services import remove_member
from buzz.subscriptions import Subscriptions
from buzz.tests.base_test_cases import TeamPermissionTestCase
from buzz.tests.factories import (
	BuzzTeamMembershipFactory,
	CommunicationFactory,
	TalkProposalFactory,
	UserFactory,
)
from buzz.tests.utils import mute_outgoing_email

SPEAKER = "subscriptions-speaker@example.com"


def mention(user: str) -> str:
	return f'<span class="mention" data-type="mention" data-id="{user}">@{user}</span>'


class TestNotificationSubscriptions(TeamPermissionTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.manager = UserFactory.create_once("subscriptions-manager@example.com").name
		BuzzTeamMembershipFactory.create(team=cls.team_a, user=cls.manager, team_role="Manager")

	def setUp(self):
		super().setUp()
		mute_outgoing_email(self)
		self.proposal = TalkProposalFactory.create(
			event=self.event_a, speakers=[{"first_name": "Speaker", "email": SPEAKER}]
		).name
		self.subscriptions = Subscriptions("Talk Proposal", self.proposal)

	def comment_as(self, user: str, content: str = "<p>Looks good</p>", **kwargs) -> str:
		with self.set_user(user):
			return add_comment("Talk Proposal", self.proposal, content, **kwargs)

	def notifications_for(self, user: str) -> list:
		return frappe.get_all(
			"Notification Log",
			filters={"for_user": user, "document_type": "Talk Proposal", "document_name": self.proposal},
			fields=["type", "from_user", "link"],
		)

	def test_comment_subscribes_author_and_notifies_other_subscribers(self):
		self.comment_as(self.alice)
		self.comment_as(self.manager)

		self.assertTrue(self.subscriptions.is_subscribed(self.alice))
		[notification] = self.notifications_for(self.alice)
		self.assertEqual(notification.type, "Buzz Activity")
		self.assertEqual(notification.from_user, self.manager)
		self.assertIn(f"proposal={self.proposal}", notification.link)
		self.assertEqual(self.notifications_for(self.manager), [])

	def test_unsubscribed_member_is_skipped_until_they_comment_again(self):
		self.comment_as(self.alice)
		self.subscriptions.unsubscribe(self.alice)

		self.comment_as(self.manager)
		self.assertEqual(self.notifications_for(self.alice), [])

		self.comment_as(self.alice)
		self.assertTrue(self.subscriptions.is_subscribed(self.alice))

	def test_mention_follows_but_keeps_an_unsubscribe(self):
		self.subscriptions.unsubscribe(self.alice)

		self.comment_as(self.manager, f"<p>{mention(self.alice)} {mention(self.bob)}</p>")

		self.assertFalse(self.subscriptions.is_subscribed(self.alice))
		# Bob is outside the team, so a mention does not reach him.
		self.assertFalse(self.subscriptions.is_subscribed(self.bob))

	def test_mentioned_member_follows_without_a_second_notification(self):
		self.comment_as(self.manager, f"<p>{mention(self.alice)} can you check?</p>")

		self.assertTrue(self.subscriptions.is_subscribed(self.alice))
		self.assertEqual(self.notifications_for(self.alice), [])

	def test_emailing_the_speaker_subscribes_and_their_reply_notifies(self):
		self.comment_as(self.alice, email_recipients=True)
		self.assertTrue(self.subscriptions.is_subscribed(self.alice))

		CommunicationFactory.create(reference_name=self.proposal, sender=SPEAKER)

		[notification] = self.notifications_for(self.alice)
		self.assertEqual(notification.type, "Buzz Activity")

	def test_member_toggles_their_subscription_and_outsider_cannot(self):
		with self.set_user(self.manager):
			set_subscription("Talk Proposal", self.proposal, True)
			self.assertTrue(get_subscription("Talk Proposal", self.proposal))
			set_subscription("Talk Proposal", self.proposal, False)
			self.assertFalse(get_subscription("Talk Proposal", self.proposal))

		with self.set_user(self.outsider), self.assertRaises(NotTeamMember):
			set_subscription("Talk Proposal", self.proposal, True)

	def test_user_whose_name_is_not_their_email_is_notified(self):
		self.subscriptions.subscribe("Administrator")

		self.comment_as(self.manager)

		self.assertEqual(len(self.notifications_for("Administrator")), 1)

	def test_deleting_a_talk_drops_its_subscriptions(self):
		self.subscriptions.subscribe(self.alice)

		frappe.delete_doc("Talk Proposal", self.proposal)

		self.assertFalse(
			frappe.db.exists("Buzz Notification Subscription", {"reference_name": self.proposal})
		)

	def test_leaving_a_team_drops_subscriptions_on_its_records_only(self):
		member = UserFactory.create_once("subscriptions-leaver@example.com").name
		for team in (self.team_a, self.team_b):
			BuzzTeamMembershipFactory.create(team=team, user=member, team_role="Manager")
		other_team = Subscriptions("Talk Proposal", TalkProposalFactory.create(event=self.event_b).name)
		self.subscriptions.subscribe(member)
		other_team.subscribe(member)

		with self.set_user(self.alice):
			remove_member(self.team_a, member)

		self.assertIsNone(self.subscriptions.row(member))
		self.assertTrue(other_team.is_subscribed(member))
