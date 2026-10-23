import frappe
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from buzz.api.comments import get_email_attachment
from buzz.api.comments.exceptions import AttachmentNotFound, NotTeamMember
from buzz.tests.base_test_cases import TeamPermissionTestCase
from buzz.tests.factories import (
	BuzzTeamMembershipFactory,
	CommunicationFactory,
	FileFactory,
	TalkProposalFactory,
	UserFactory,
)

SPEAKER = "attachments-speaker@example.com"
CONTENT = b"stage layout"


class TestEmailAttachments(TeamPermissionTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.viewer = UserFactory.create_once("attachments-viewer@example.com").name
		cls.speaker = UserFactory.create_once(SPEAKER).name
		cls.other_team_viewer = UserFactory.create_once("attachments-other-viewer@example.com").name
		BuzzTeamMembershipFactory.create(team=cls.team_a, user=cls.viewer, team_role="Viewer")
		BuzzTeamMembershipFactory.create(team=cls.team_b, user=cls.other_team_viewer, team_role="Viewer")

	def setUp(self):
		super().setUp()
		# send_private_file reads the request's environ and headers.
		frappe.local.request = Request(EnvironBuilder().get_environ())
		self.proposal = TalkProposalFactory.create(
			event=self.event_a, speakers=[{"first_name": "Speaker", "email": SPEAKER}]
		).name
		email = CommunicationFactory.create(reference_name=self.proposal).name
		self.file = self.private_file("Communication", email)

	def private_file(self, doctype: str | None = None, name: str | None = None) -> str:
		return FileFactory.create(
			content=CONTENT, is_private=1, attached_to_doctype=doctype, attached_to_name=name
		).name

	def download_as(self, user: str, file: str):
		with self.set_user(user):
			return get_email_attachment(file)

	def test_event_team_member_without_desk_access_downloads(self):
		self.assertNotEqual(frappe.db.get_value("User", self.viewer, "user_type"), "System User")

		response = self.download_as(self.viewer, self.file)
		response.direct_passthrough = False

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.get_data(), CONTENT)

	def test_members_of_other_teams_are_refused(self):
		for user in (self.bob, self.other_team_viewer):
			with self.assertRaises(NotTeamMember):
				self.download_as(user, self.file)

	def test_users_in_no_team_are_refused(self):
		for user in (self.outsider, self.speaker):
			self.assertFalse(frappe.db.exists("Buzz Team Membership", {"user": user}))
			with self.assertRaises(NotTeamMember):
				self.download_as(user, self.file)

	def test_private_file_stays_closed_outside_the_endpoint(self):
		for user in (self.bob, self.other_team_viewer, self.outsider, self.speaker):
			with self.set_user(user):
				self.assertFalse(frappe.has_permission("File", "read", doc=self.file))

	def test_only_files_on_a_record_email_are_served(self):
		unlinked_email = CommunicationFactory.create(reference_doctype=None, reference_name=None).name
		for file in (
			self.private_file("Talk Proposal", self.proposal),
			self.private_file(),
			self.private_file("Communication", unlinked_email),
			"missing-file",
		):
			with self.assertRaises(AttachmentNotFound):
				self.download_as(self.alice, file)
