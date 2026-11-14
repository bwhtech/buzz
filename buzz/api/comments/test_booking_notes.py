from io import BytesIO
from unittest.mock import patch

import frappe
from pypdf import PdfWriter

from buzz.api.booking.exceptions import InvoiceUnavailable
from buzz.api.comments import add_comment, get_activity
from buzz.api.comments.exceptions import InvalidAttachment, NoRecipients
from buzz.comments import dashboard_url, note_email_args
from buzz.tests.base_test_cases import TeamPermissionTestCase, create_paid_ticket_type
from buzz.tests.factories import BuzzTeamMembershipFactory, EventBookingFactory, FileFactory, UserFactory
from buzz.tests.utils import mute_outgoing_email

BUYER_EMAIL = "booking-notes-buyer@example.com"
BOOKER = "booking-notes-booker@example.com"


def blank_pdf() -> bytes:
	writer, buffer = PdfWriter(), BytesIO()
	writer.add_blank_page(width=100, height=100)
	writer.write(buffer)
	return buffer.getvalue()


PDF = blank_pdf()


class TestBookingNotes(TeamPermissionTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.manager = UserFactory.create_once("booking-notes-manager@example.com").name
		cls.booker = UserFactory.create_once(BOOKER).name
		BuzzTeamMembershipFactory.create(team=cls.team_a, user=cls.manager, team_role="Manager")
		cls.ticket_type = create_paid_ticket_type(cls.event_a).name

	def setUp(self):
		super().setUp()
		mute_outgoing_email(self)
		self.booking = self.create_booking(buyer_email=BUYER_EMAIL)

	def create_booking(self, attendees: int = 2, **overrides):
		booking = EventBookingFactory.create(
			event=self.event_a,
			user=self.booker,
			payment_status="Paid",
			attendees=[
				{
					"ticket_type": self.ticket_type,
					"first_name": f"Guest {index}",
					"email": f"g{index}@example.com",
				}
				for index in range(attendees)
			],
			**overrides,
		)
		booking.submit()
		return booking

	def email_as(self, user: str, booking: str | None = None, **kwargs) -> str:
		with self.set_user(user):
			return add_comment(
				"Event Booking", booking or self.booking.name, "<p>Hello</p>", email_recipients=True, **kwargs
			)

	def attachment_names(self, communication: str) -> list[str]:
		return frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Communication", "attached_to_name": communication},
			pluck="file_name",
			order_by="creation asc",
		)

	def queued_attachments(self) -> list[str]:
		"""Frappe adds queued attachments to the message when it sends, so they show on the queue row."""
		queue = frappe.get_all(
			"Email Queue", {"reference_name": self.booking.name}, pluck="attachments", limit=1
		)
		return queue and queue[0]

	def test_note_is_emailed_to_the_buyer(self):
		name = self.email_as(self.manager)

		self.assertEqual(frappe.db.get_value("Communication", name, "recipients"), BUYER_EMAIL)
		self.assertIn(BUYER_EMAIL, self.queued_recipients())

	def queued_recipients(self) -> list[str]:
		queues = frappe.get_all("Email Queue", {"reference_name": self.booking.name}, pluck="name")
		return frappe.get_all("Email Queue Recipient", {"parent": ("in", queues)}, pluck="recipient")

	def test_note_falls_back_to_the_booking_user(self):
		booking = self.create_booking(buyer_email="")

		name = self.email_as(self.manager, booking.name)

		self.assertEqual(frappe.db.get_value("Communication", name, "recipients"), BOOKER)

	def test_email_args_name_the_booking_and_event(self):
		args = note_email_args("Event Booking", self.booking.name, self.manager, "<p>Hi</p>")

		event_title = frappe.db.get_value("Buzz Event", self.event_a, "title")
		self.assertEqual(args["record_title"], f"Booking {self.booking.name} · {event_title}")

	def test_dashboard_url_opens_the_booking_drawer(self):
		url = dashboard_url("Event Booking", self.booking.name)

		self.assertTrue(
			url.endswith(f"/b/manage/events/{self.event_a}/transactions?booking={self.booking.name}")
		)

	def test_booking_note_has_no_proposal_wording(self):
		self.email_as(self.manager)

		message = frappe.get_all("Email Queue", {"reference_name": self.booking.name}, pluck="message")[0]
		self.assertIn("A note on your booking", message)
		self.assertNotIn("proposal", message)

	def test_generated_pdfs_and_an_upload_are_saved_on_the_email(self):
		with self.set_user(self.manager):
			upload = FileFactory.create(file_name="layout.txt", is_private=1, content=b"layout").name
		ticket = frappe.db.get_value("Event Ticket", {"booking": self.booking.name}, "name")
		attachments = [
			{"kind": "tickets"},
			{"kind": "ticket", "ticket": ticket},
			{"kind": "file", "file": upload},
		]

		with (
			patch("buzz.api.comments.attachments.booking_tickets_pdf", return_value=PDF),
			patch("buzz.api.comments.attachments.ticket_pdf", return_value=PDF),
		):
			name = self.email_as(self.manager, attachments=attachments)

		self.assertEqual(
			self.attachment_names(name),
			[f"Tickets-{self.booking.name}.pdf", f"Ticket-{ticket}.pdf", "layout.txt"],
		)
		files = frappe.get_all("File", {"attached_to_name": name}, pluck="name")
		self.assertEqual(
			sorted(row["fid"] for row in frappe.parse_json(self.queued_attachments())), sorted(files)
		)

	def test_activity_feed_lists_the_attachments(self):
		with patch("buzz.api.comments.attachments.booking_tickets_pdf", return_value=PDF):
			self.email_as(self.manager, attachments=[{"kind": "tickets"}])

		with self.set_user(self.manager):
			feed = get_activity("Event Booking", self.booking.name)

		email = next(entry for entry in feed if entry.kind == "email")
		self.assertEqual([file.name for file in email.attachments], [f"Tickets-{self.booking.name}.pdf"])

	def test_invoice_needs_an_invoice_on_the_booking(self):
		with self.assertRaises(InvoiceUnavailable):
			self.email_as(self.manager, attachments=[{"kind": "invoice"}])

	def test_invoice_is_attached(self):
		with patch("buzz.api.comments.attachments.booking_invoice_pdf", return_value=PDF):
			name = self.email_as(self.manager, attachments=[{"kind": "invoice"}])

		self.assertEqual(self.attachment_names(name), [f"Invoice-{self.booking.name}.pdf"])

	def test_ticket_of_another_booking_is_refused(self):
		other = self.create_booking(attendees=1)
		ticket = frappe.db.get_value("Event Ticket", {"booking": other.name}, "name")

		with self.assertRaises(InvalidAttachment):
			self.email_as(self.manager, attachments=[{"kind": "ticket", "ticket": ticket}])

	def test_uploads_must_be_the_senders_own_private_unattached_files(self):
		with self.set_user(self.alice):
			others = FileFactory.create(is_private=1).name
		with self.set_user(self.manager):
			public = FileFactory.create(is_private=0).name
			attached = FileFactory.create(
				is_private=1, attached_to_doctype="Event Booking", attached_to_name=self.booking.name
			).name

		for file in (others, public, attached, "missing-file"):
			with self.assertRaises(InvalidAttachment):
				self.email_as(self.manager, attachments=[{"kind": "file", "file": file}])

	def test_malformed_attachments_are_refused(self):
		for attachment in ({"kind": "zip"}, {"kind": "file"}, {"kind": "ticket"}, {}):
			with self.assertRaises(InvalidAttachment):
				self.email_as(self.manager, attachments=[attachment])

	def test_booking_attachments_are_only_for_booking_notes(self):
		proposal_attachment = {"kind": "tickets"}
		from buzz.tests.factories import TalkProposalFactory

		proposal = TalkProposalFactory.create(
			event=self.event_a,
			speakers=[{"first_name": "Speaker", "email": "booking-notes-speaker@example.com"}],
		).name

		with self.set_user(self.manager), self.assertRaises(InvalidAttachment):
			add_comment(
				"Talk Proposal",
				proposal,
				"<p>Hi</p>",
				email_recipients=True,
				attachments=[proposal_attachment],
			)

	def test_attachments_are_ignored_on_a_team_note(self):
		with self.set_user(self.manager):
			name = add_comment(
				"Event Booking", self.booking.name, "<p>Internal</p>", attachments=[{"kind": "zip"}]
			)

		self.assertTrue(frappe.db.exists("Comment", name))
