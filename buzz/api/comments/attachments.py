"""What an emailed note can carry: a booking's invoice or tickets, or a file the sender uploaded."""

import frappe
from pydantic import ValidationError

from buzz.api.booking.downloads import booking_invoice_pdf, booking_tickets_pdf, ticket_pdf
from buzz.api.comments.exceptions import InvalidAttachment
from buzz.api.comments.schemas import AttachmentRequest

# What each record can render as a PDF of its own.
RECORD_KINDS = {"Event Booking": {"invoice", "tickets", "ticket"}, "Event Ticket": {"ticket"}}


class EmailAttachments:
	"""Resolves requested attachments to what `Communication` stores: generated PDFs as
	`{"fname", "fcontent"}` and uploads as File names."""

	def __init__(self, reference_doctype: str, reference_name: str):
		self.reference_doctype = reference_doctype
		self.reference_name = reference_name

	def resolve(self, requested: list[dict] | None) -> list[str | dict]:
		return [self.attachment(self.parse(item)) for item in requested or []]

	def parse(self, item: dict) -> AttachmentRequest:
		try:
			request = AttachmentRequest(**item)
		except (ValidationError, TypeError):
			InvalidAttachment.throw()
		if request.kind != "file" and request.kind not in RECORD_KINDS.get(self.reference_doctype, ()):
			InvalidAttachment.throw()
		return request

	def attachment(self, request: AttachmentRequest) -> str | dict:
		if request.kind == "file":
			return self.uploaded_file(request.file)
		if request.kind == "ticket":
			return self.ticket(request.ticket)
		if request.kind == "tickets":
			return {
				"fname": f"Tickets-{self.reference_name}.pdf",
				"fcontent": booking_tickets_pdf(self.reference_name),
			}
		return {
			"fname": f"Invoice-{self.reference_name}.pdf",
			"fcontent": booking_invoice_pdf(self.reference_name),
		}

	def ticket(self, ticket: str | None) -> dict:
		if not ticket or not self.owns_ticket(ticket):
			InvalidAttachment.throw()
		return {"fname": f"Ticket-{ticket}.pdf", "fcontent": ticket_pdf(ticket)}

	def owns_ticket(self, ticket: str) -> bool:
		if self.reference_doctype == "Event Ticket":
			return ticket == self.reference_name
		return frappe.db.get_value("Event Ticket", ticket, "booking") == self.reference_name

	def uploaded_file(self, file: str | None) -> str:
		row = file and frappe.db.get_value(
			"File", file, ["owner", "is_private", "attached_to_doctype", "attached_to_name"], as_dict=True
		)
		if not (
			row
			and row.is_private
			and row.owner == frappe.session.user
			and not row.attached_to_doctype
			and not row.attached_to_name
		):
			InvalidAttachment.throw()
		return file
