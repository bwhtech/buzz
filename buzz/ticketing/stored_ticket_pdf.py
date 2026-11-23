"""Frappe keeps a private copy of every print it attaches to an email (System Settings >
Store Attached PDF Document) and never deletes it. A ticket renders again at will, so the
copies of emailed tickets are deleted."""

import frappe

BATCH_SIZE = 500
FILE_FIELDS = ["name", "file_name", "content_hash", "attached_to_name"]


class StoredTicketPdf:
	"""A copy on an Email Queue is named `<ticket>.pdf`, or `<ticket><suffix>.pdf` when that
	name was taken on disk, the suffix being the end of its content hash."""

	def __init__(self, file):
		self.file = file

	def ticket(self) -> str | None:
		if not (self.file.file_name or "").endswith(".pdf"):
			return None
		stem = self.file.file_name.removesuffix(".pdf")
		suffix = (self.file.content_hash or "")[-6:]
		return stem.removesuffix(suffix) if suffix else stem

	def is_for(self, reference: dict | None) -> bool:
		"""The queue row's reference is exact. Hash names of different doctypes could collide."""
		return bool(reference) and (reference.reference_doctype, reference.reference_name) == (
			"Event Ticket",
			self.ticket(),
		)


def delete_after_send(file, method=None):
	"""File `after_insert`. The Email Queue stores the copy while it builds the message, before
	handing it to SMTP, and never reads it back: a retry renders the ticket again. The job is
	only queued by the commit that follows the send."""
	if file.attached_to_doctype == "Email Queue" and StoredTicketPdf(file).is_for(queue_reference(file)):
		frappe.enqueue(
			"buzz.ticketing.stored_ticket_pdf.delete_stored_copy", file=file.name, enqueue_after_commit=True
		)


def queue_reference(file) -> dict | None:
	return frappe.db.get_value(
		"Email Queue", file.attached_to_name, ["reference_doctype", "reference_name"], as_dict=True
	)


def delete_stored_copy(file: str):
	# Detached first, or deleting logs an "Attachment Removed" comment on the Email Queue.
	frappe.db.set_value("File", file, {"attached_to_doctype": None, "attached_to_name": None})
	frappe.delete_doc("File", file, ignore_permissions=True)


def delete_stored_ticket_pdfs():
	"""Copies stored before `delete_after_send`, mostly of queue rows Frappe has since purged."""
	last_name = ""
	while files := pdfs_on_email_queues(after=last_name):
		for file in ticket_copies(files):
			delete_stored_copy(file)
		frappe.db.commit()  # nosemgrep: frappe-manual-commit
		last_name = files[-1].name


def pdfs_on_email_queues(after: str) -> list:
	return frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Email Queue", "file_name": ["like", "%.pdf"], "name": [">", after]},
		fields=FILE_FIELDS,
		order_by="name asc",
		limit=BATCH_SIZE,
	)


def ticket_copies(files: list) -> list[str]:
	"""A purged queue row leaves only the name to go by, and a collision is improbable."""
	queues = existing(
		"Email Queue", [file.attached_to_name for file in files], ["reference_doctype", "reference_name"]
	)
	tickets = existing("Event Ticket", [StoredTicketPdf(file).ticket() for file in files])
	return [file.name for file in files if is_ticket_copy(file, queues, tickets)]


def is_ticket_copy(file, queues: dict, tickets: dict) -> bool:
	pdf, queue = StoredTicketPdf(file), queues.get(file.attached_to_name)
	if queue:
		return pdf.is_for(queue)
	return pdf.ticket() in tickets


def existing(doctype: str, names: list, fields: list | None = None) -> dict:
	rows = frappe.get_all(
		doctype, filters={"name": ["in", [name for name in names if name]]}, fields=["name", *(fields or [])]
	)
	return {row.name: row for row in rows}
