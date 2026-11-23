from unittest.mock import patch

import frappe

from buzz.api.comments import add_comment
from buzz.api.comments.exceptions import InvalidAttachment
from buzz.api.comments.test_booking_notes import PDF
from buzz.comments import dashboard_url, note_email_args
from buzz.tests.base_test_cases import TeamPermissionTestCase
from buzz.tests.factories import BuzzTeamMembershipFactory, EventTicketFactory, UserFactory
from buzz.tests.utils import mute_outgoing_email

ATTENDEE = "ticket-notes-attendee@example.com"


class TestTicketNotes(TeamPermissionTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.manager = UserFactory.create_once("ticket-notes-manager@example.com").name
		BuzzTeamMembershipFactory.create(team=cls.team_a, user=cls.manager, team_role="Manager")

	def setUp(self):
		super().setUp()
		mute_outgoing_email(self)
		self.ticket = self.create_ticket()

	def create_ticket(self) -> str:
		return EventTicketFactory.create("submitted", event=self.event_a, attendee_email=ATTENDEE).name

	def email_as(self, user: str, **kwargs) -> str:
		with self.set_user(user):
			return add_comment("Event Ticket", self.ticket, "<p>Hello</p>", email_recipients=True, **kwargs)

	def test_note_stays_with_the_team(self):
		with self.set_user(self.manager):
			name = add_comment("Event Ticket", self.ticket, "<p>Aisle seat</p>")

		self.assertEqual(frappe.db.get_value("Comment", name, "reference_name"), self.ticket)

	def test_note_is_emailed_to_the_attendee(self):
		name = self.email_as(self.manager)

		self.assertEqual(frappe.db.get_value("Communication", name, "recipients"), ATTENDEE)

	def test_own_ticket_pdf_is_attached(self):
		with patch("buzz.api.comments.attachments.ticket_pdf", return_value=PDF):
			name = self.email_as(self.manager, attachments=[{"kind": "ticket", "ticket": self.ticket}])

		files = frappe.get_all(
			"File", {"attached_to_doctype": "Communication", "attached_to_name": name}, pluck="file_name"
		)
		self.assertEqual(files, [f"Ticket-{self.ticket}.pdf"])

	def test_another_ticket_or_a_booking_file_is_refused(self):
		other = self.create_ticket()
		for attachment in ({"kind": "ticket", "ticket": other}, {"kind": "invoice"}, {"kind": "tickets"}):
			with self.assertRaises(InvalidAttachment):
				self.email_as(self.manager, attachments=[attachment])

	def test_email_and_link_name_the_ticket(self):
		event_title = frappe.db.get_value("Buzz Event", self.event_a, "title")
		args = note_email_args("Event Ticket", self.ticket, self.manager, "<p>Hi</p>")

		self.assertEqual(args["record_title"], f"Ticket {self.ticket} · {event_title}")
		self.assertTrue(
			dashboard_url("Event Ticket", self.ticket).endswith(
				f"/b/manage/events/{self.event_a}/guests?guest={self.ticket}"
			)
		)
