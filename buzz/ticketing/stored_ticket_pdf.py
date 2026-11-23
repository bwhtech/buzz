"""Frappe keeps a private copy of every print it attaches to an email (System Settings >
Store Attached PDF Document) and never deletes it. A ticket renders again at will, so the
copies of emailed tickets are deleted."""

import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import Concat

BATCH_SIZE = 500


def delete_after_send(file, method=None):
	"""File `after_insert`. The Email Queue stores the copy while it builds the message, before
	handing it to SMTP, and never reads it back: a retry renders the ticket again. The job is
	only queued by the commit that follows the send."""
	if is_ticket_pdf(file):
		frappe.enqueue(
			"buzz.ticketing.stored_ticket_pdf.delete_stored_copy", file=file.name, enqueue_after_commit=True
		)


def is_ticket_pdf(file) -> bool:
	return (
		file.attached_to_doctype == "Email Queue"
		and (file.file_name or "").endswith(".pdf")
		and bool(frappe.db.exists("Event Ticket", file.file_name.removesuffix(".pdf")))
	)


def delete_stored_copy(file: str):
	# Detached first, or deleting logs an "Attachment Removed" comment on the Email Queue.
	frappe.db.set_value("File", file, {"attached_to_doctype": None, "attached_to_name": None})
	frappe.delete_doc("File", file, ignore_permissions=True)


def delete_stored_ticket_pdfs():
	"""Copies stored before `delete_after_send`, mostly of queue rows Frappe has since purged."""
	while files := stored_ticket_pdfs():
		for file in files:
			delete_stored_copy(file)
		frappe.db.commit()  # nosemgrep: frappe-manual-commit


def stored_ticket_pdfs() -> list[str]:
	File, Ticket = DocType("File"), DocType("Event Ticket")
	return (
		frappe.qb.from_(File)
		.join(Ticket)
		.on(File.file_name == Concat(Ticket.name, ".pdf"))
		.select(File.name)
		.where(File.attached_to_doctype == "Email Queue")
		.limit(BATCH_SIZE)
		.run(pluck=True)
	)
