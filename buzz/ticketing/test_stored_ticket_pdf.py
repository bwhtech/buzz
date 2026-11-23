from io import BytesIO
from unittest.mock import patch

import frappe
from frappe.email.doctype.email_queue.email_queue import SendMailContext
from frappe.tests import IntegrationTestCase
from pypdf import PdfWriter

from buzz.patches.delete_stored_ticket_pdfs import execute as run_cleanup_patch
from buzz.tests.factories import BuzzEventFactory, EventTicketFactory, FileFactory
from buzz.tests.utils import mute_outgoing_email, stub_pdf_rendering
from buzz.ticketing.stored_ticket_pdf import delete_stored_ticket_pdfs

DELETE_JOB = "buzz.ticketing.stored_ticket_pdf.delete_stored_copy"


class TestStoredTicketPdf(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = BuzzEventFactory.create(
			send_ticket_email=1, attach_email_ticket=1, attach_calendar_invite=0
		)

	def setUp(self):
		mute_outgoing_email(self)
		self.enterContext(stub_pdf_rendering())
		self.enterContext(self.change_settings("System Settings", store_attached_pdf_document=1))
		self.ticket = EventTicketFactory.create(event=self.event.name)

	def queue_ticket_email(self) -> SendMailContext:
		self.ticket.send_ticket_email()
		queue = frappe.get_last_doc("Email Queue", {"reference_name": self.ticket.name})
		return SendMailContext(queue)

	def build_message(self, context: SendMailContext) -> str:
		"""What `EmailQueue.send` does for each recipient before handing the message to SMTP."""
		return context.build_message(self.ticket.attendee_email).decode()

	def stored_copy(self) -> str | None:
		return frappe.db.get_value(
			"File", {"file_name": f"{self.ticket.name}.pdf", "attached_to_doctype": "Email Queue"}
		)

	def test_deletion_is_queued_for_after_the_send_commits(self):
		with patch("buzz.ticketing.stored_ticket_pdf.frappe.enqueue") as enqueue:
			self.build_message(self.queue_ticket_email())

		enqueue.assert_called_once_with(DELETE_JOB, file=self.stored_copy(), enqueue_after_commit=True)

	def test_a_retried_send_still_attaches_the_ticket_once_the_copy_is_gone(self):
		self.build_message(self.queue_ticket_email())
		frappe.delete_doc("File", self.stored_copy(), ignore_permissions=True)

		message = self.build_message(self.queue_ticket_email())

		self.assertIn(f'filename="{self.ticket.name}.pdf"', message)

	def test_the_job_deletes_the_copy_without_commenting_on_the_email_queue(self):
		self.build_message(self.queue_ticket_email())
		file = self.stored_copy()
		queue = frappe.db.get_value("File", file, "attached_to_name")

		frappe.get_attr(DELETE_JOB)(file=file)

		self.assertFalse(frappe.db.exists("File", file))
		self.assertFalse(
			frappe.db.exists("Comment", {"reference_name": queue, "comment_type": "Attachment Removed"})
		)

	def test_other_pdfs_on_an_email_queue_are_left_alone(self):
		with patch("buzz.ticketing.stored_ticket_pdf.frappe.enqueue") as enqueue:
			FileFactory.create(
				file_name="Invoice-0001.pdf",
				content=unique_pdf(),
				is_private=1,
				attached_to_doctype="Email Queue",
				attached_to_name=frappe.generate_hash(length=10),
			)

		enqueue.assert_not_called()

	def test_cleanup_deletes_copies_left_behind_by_deleted_queue_rows(self):
		orphan = self.stored_pdf(f"{self.ticket.name}.pdf", attached_to_doctype="Email Queue")
		invoice = self.stored_pdf("Invoice-0001.pdf", attached_to_doctype="Email Queue")
		ticket_elsewhere = self.stored_pdf(f"{self.ticket.name}.pdf", attached_to_doctype="Communication")

		with patch("frappe.db.commit"):
			delete_stored_ticket_pdfs()

		self.assertFalse(frappe.db.exists("File", orphan))
		self.assertTrue(frappe.db.exists("File", invoice))
		self.assertTrue(frappe.db.exists("File", ticket_elsewhere))

	def test_patch_queues_the_cleanup_on_the_long_queue(self):
		with patch("buzz.patches.delete_stored_ticket_pdfs.frappe.enqueue") as enqueue:
			run_cleanup_patch()

		enqueue.assert_called_once()
		self.assertEqual(enqueue.call_args.kwargs["queue"], "long")

	def stored_pdf(self, file_name: str, attached_to_doctype: str) -> str:
		with patch("buzz.ticketing.stored_ticket_pdf.frappe.enqueue"):
			return FileFactory.create(
				file_name=file_name,
				content=unique_pdf(),
				is_private=1,
				attached_to_doctype=attached_to_doctype,
				attached_to_name=frappe.generate_hash(length=10),
			).name


def unique_pdf() -> bytes:
	"""Files with the same content share one file on disk."""
	writer, buffer = PdfWriter(), BytesIO()
	writer.add_blank_page(width=100, height=100)
	writer.add_metadata({"/Title": frappe.generate_hash()})
	writer.write(buffer)
	return buffer.getvalue()
