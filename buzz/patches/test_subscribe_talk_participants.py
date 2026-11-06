import frappe

from buzz.api.comments import add_comment
from buzz.patches.subscribe_talk_participants import execute
from buzz.subscriptions import Subscriptions
from buzz.tests.base_test_cases import TeamPermissionTestCase
from buzz.tests.factories import (
	BuzzTeamMembershipFactory,
	CommunicationFactory,
	TalkProposalFactory,
	UserFactory,
)
from buzz.tests.utils import mute_outgoing_email


class TestSubscribeTalkParticipants(TeamPermissionTestCase):
	def setUp(self):
		super().setUp()
		mute_outgoing_email(self)
		self.manager = UserFactory.create_once("backfill-manager@example.com").name
		self.leaver = UserFactory.create_once("backfill-leaver@example.com").name
		for user in (self.manager, self.leaver):
			BuzzTeamMembershipFactory.create(team=self.team_a, user=user, team_role="Manager")
		self.proposal = TalkProposalFactory.create(event=self.event_a).name
		self.subscriptions = Subscriptions("Talk Proposal", self.proposal)

	def test_subscribes_current_members_who_wrote_notes_or_emails(self):
		for user in (self.alice, self.leaver):
			with self.set_user(user):
				add_comment("Talk Proposal", self.proposal, "<p>Before subscriptions</p>")
		CommunicationFactory.create(
			reference_name=self.proposal, sent_or_received="Sent", sender=f"Manager <{self.manager}>"
		)
		frappe.db.delete("Buzz Notification Subscription", {"reference_name": self.proposal})
		frappe.db.set_value("Buzz Team Membership", {"team": self.team_a, "user": self.leaver}, "enabled", 0)
		self.subscriptions.unsubscribe(self.alice)

		execute()

		self.assertTrue(self.subscriptions.is_subscribed(self.manager))
		self.assertFalse(self.subscriptions.is_subscribed(self.alice))
		self.assertIsNone(self.subscriptions.row(self.leaver))
