from unittest.mock import patch

import frappe
from frappe.desk.form.utils import update_comment

from buzz.api.comments import add_comment, delete_comment, get_activity, get_mention_members
from buzz.api.comments.exceptions import CannotDeleteComment, NotCommentable, NotTeamMember
from buzz.tests.base_test_cases import TeamPermissionTestCase
from buzz.tests.factories import BuzzTeamMembershipFactory, CommentFactory, TalkProposalFactory, UserFactory
from buzz.tests.utils import mute_outgoing_email

SPEAKER = "comments-speaker@example.com"


def mention(user: str) -> str:
	return f'<span class="mention" data-type="mention" data-id="{user}">@{user}</span>'


def emailed_to(reference_name: str) -> set[str]:
	queues = frappe.get_all(
		"Email Queue",
		filters={"reference_doctype": "Talk Proposal", "reference_name": reference_name},
		pluck="name",
	)
	return set(frappe.get_all("Email Queue Recipient", filters={"parent": ("in", queues)}, pluck="recipient"))


class TestDocumentComments(TeamPermissionTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.viewer = UserFactory.create_once("comments-viewer@example.com").name
		cls.manager = UserFactory.create_once("comments-manager@example.com").name
		cls.speaker = UserFactory.create_once(SPEAKER).name
		BuzzTeamMembershipFactory.create(team=cls.team_a, user=cls.viewer, team_role="Viewer")
		BuzzTeamMembershipFactory.create(team=cls.team_a, user=cls.manager, team_role="Manager")

	def setUp(self):
		super().setUp()
		mute_outgoing_email(self)
		self.proposal = TalkProposalFactory.create(
			event=self.event_a, speakers=[{"first_name": "Speaker", "email": SPEAKER}]
		).name

	def add_as(self, user: str, content: str = "<p>Strong opener</p>", **kwargs) -> str:
		with self.set_user(user):
			return add_comment("Talk Proposal", self.proposal, content, **kwargs)

	def feed_as(self, user: str) -> list:
		with self.set_user(user):
			return get_activity("Talk Proposal", self.proposal)

	def comments_as(self, user: str) -> list:
		return [entry for entry in self.feed_as(user) if entry.kind == "comment"]

	def test_every_member_comments_and_reads_the_thread(self):
		self.add_as(self.alice, "<p>First</p>")
		self.add_as(self.viewer, "<p>Second</p>")

		comments = self.comments_as(self.manager)

		self.assertEqual([c.owner for c in comments], [self.alice, self.viewer])
		self.assertIn("Second", comments[1].content)

	def test_speaker_and_outsider_are_kept_out(self):
		self.add_as(self.alice)

		for user in (self.speaker, self.outsider, self.bob):
			with self.assertRaises(NotTeamMember):
				self.feed_as(user)
			with self.assertRaises(NotTeamMember):
				self.add_as(user)

	def test_author_is_the_session_user(self):
		name = self.add_as(self.viewer)

		self.assertEqual(
			frappe.db.get_value("Comment", name, ["comment_email", "owner"]), (self.viewer, self.viewer)
		)

	def test_other_doctypes_are_refused(self):
		with self.set_user(self.alice), self.assertRaises(NotCommentable):
			get_activity("Buzz Event", str(self.event_a))

	def test_note_is_not_cached_on_the_proposal(self):
		self.add_as(self.alice)

		self.assertIsNone(frappe.db.get_value("Talk Proposal", self.proposal, "_comments"))

	def test_live_update_goes_to_member_rooms_only(self):
		with patch("buzz.comments.frappe.publish_realtime") as publish:
			self.add_as(self.alice)

		about_proposal = [
			call
			for call in publish.call_args_list
			if call.kwargs.get("docname") == self.proposal or call.args[0] == "buzz_comment_update"
		]
		self.assertEqual(
			{call.kwargs.get("user") for call in about_proposal}, {self.alice, self.viewer, self.manager}
		)

	def test_mention_list_is_the_team(self):
		with self.set_user(self.viewer):
			members = {member.user for member in get_mention_members("Talk Proposal", self.proposal)}

		self.assertEqual(members, {self.alice, self.viewer, self.manager})

	def test_only_mentioned_members_are_emailed(self):
		self.add_as(self.alice, f"<p>{mention(self.manager)} {mention(self.outsider)} take a look</p>")

		self.assertEqual(emailed_to(self.proposal), {self.manager})

	def test_plain_note_emails_no_one(self):
		self.add_as(self.alice)

		self.assertEqual(emailed_to(self.proposal), set())

	def test_note_emailed_to_speakers_is_an_email_not_a_comment(self):
		name = self.add_as(self.manager, "<p>Slow down on slide 4</p>", email_recipients=True)

		communication = frappe.get_doc("Communication", name)
		self.assertEqual((communication.reference_name, communication.recipients), (self.proposal, SPEAKER))
		self.assertEqual(self.comments_as(self.manager), [])

	def test_emailed_note_is_sanitized(self):
		name = self.add_as(self.manager, '<p>Hi</p><img src=x onerror="alert(1)">', email_recipients=True)

		self.assertNotIn("onerror", frappe.db.get_value("Communication", name, "content"))

	def test_feed_holds_creation_notes_emails_and_status_changes_in_order(self):
		self.add_as(self.alice, "<p>Mock went well</p>")
		self.add_as(self.manager, "<p>Slow down on slide 4</p>", email_recipients=True)
		self.change_proposal(status="Shortlisted")

		feed = self.feed_as(self.viewer)

		self.assertEqual([entry.kind for entry in feed], ["created", "comment", "email", "change"])
		self.assertEqual(feed[2].recipients, [SPEAKER])
		self.assertEqual((feed[3].field, feed[3].new_value), ("status", "Shortlisted"))

	def test_untracked_field_edits_stay_out_of_the_feed(self):
		self.change_proposal(phone="+91-9820000000")

		self.assertEqual([entry.kind for entry in self.feed_as(self.alice)], ["created"])

	def change_proposal(self, **values):
		proposal = frappe.get_doc("Talk Proposal", self.proposal)
		proposal.update(values)
		# Frappe skips Version rows under tests unless asked for them.
		proposal.save(ignore_version=False)

	def test_author_edits_through_frappe(self):
		name = self.add_as(self.viewer)

		with self.set_user(self.viewer):
			update_comment(name, "<p>Edited</p>")

		self.assertEqual(frappe.db.get_value("Comment", name, "content"), "<p>Edited</p>")

	def test_author_and_team_admin_delete(self):
		own, others = self.add_as(self.viewer), self.add_as(self.viewer)

		with self.set_user(self.viewer):
			delete_comment(own)
		with self.set_user(self.alice):
			delete_comment(others)

		self.assertFalse(frappe.db.exists("Comment", {"name": ("in", [own, others])}))

	def test_manager_cannot_delete_someone_elses_comment(self):
		name = self.add_as(self.viewer)

		with self.set_user(self.manager), self.assertRaises(CannotDeleteComment):
			delete_comment(name)

	def test_activity_logs_cannot_be_deleted(self):
		log = CommentFactory.create(comment_type="Info", reference_name=self.proposal)

		with self.set_user(self.alice), self.assertRaises(frappe.DoesNotExistError):
			delete_comment(log.name)
