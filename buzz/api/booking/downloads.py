"""Files a booking's confirmation page hands out: the calendar invite and the tickets."""

from io import BytesIO
from typing import TYPE_CHECKING

import frappe
from pypdf import PdfWriter

from buzz.api.booking.details import ensure_confirmation_access
from buzz.events.online_meeting import OnlineMeeting
from buzz.utils import generate_ics_file, qr_data_uri

if TYPE_CHECKING:
	from buzz.ticketing.doctype.event_ticket.event_ticket import EventTicket


def calendar_invite(booking_id: str, token: str | None) -> None:
	ensure_confirmation_access(booking_id, token)
	booking = frappe.get_cached_doc("Event Booking", booking_id)
	event = frappe.get_cached_doc("Buzz Event", booking.event)
	attendee_email = booking.buyer_email or booking.user
	send_file(f"{event.title}.ics", generate_ics_file(event, attendee_email, OnlineMeeting(event)))


def tickets_pdf(booking_id: str, token: str | None) -> None:
	ensure_confirmation_access(booking_id, token)
	event = frappe.db.get_value("Event Booking", booking_id, "event")
	print_format = frappe.db.get_value("Buzz Event", event, "ticket_print_format") or "Standard Ticket"
	tickets = frappe.db.get_all("Event Ticket", {"booking": booking_id, "docstatus": 1}, pluck="name")
	send_file(f"Tickets-{booking_id}.pdf", render_tickets(tickets, print_format))


def render_tickets(tickets: list[str], print_format: str) -> bytes:
	# Access to the booking was checked above; a guest holding only the token has no
	# permission of their own on the tickets for frappe's print check to find.
	frappe.flags.ignore_print_permissions = True
	try:
		writer = PdfWriter()
		for name in tickets:
			frappe.get_print(
				"Event Ticket", name, print_format, doc=inlined_qr(name), as_pdf=True, output=writer
			)
		buffer = BytesIO()
		writer.write(buffer)
		return buffer.getvalue()
	finally:
		frappe.flags.ignore_print_permissions = False


def inlined_qr(name: str) -> "EventTicket":
	# The QR is a private file, which frappe inlines into the PDF only for a user who may
	# read it. A guest may not, so the ticket goes in with the image already inlined.
	ticket = frappe.get_doc("Event Ticket", name)
	ticket.qr_code = qr_data_uri(name)
	return ticket


def send_file(filename: str, content: str | bytes) -> None:
	frappe.response.filename = filename
	frappe.response.filecontent = content
	frappe.response.type = "download"
