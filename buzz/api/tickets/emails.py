import frappe
from frappe import _
from frappe.utils import escape_html

from buzz.emails import send_message_email


def send_ticket_transfer_emails(ticket_id: str, old_name: str, old_email: str, new_name: str, new_email: str):
	try:
		ticket = frappe.get_doc("Event Ticket", ticket_id)
		event = frappe.get_doc("Buzz Event", ticket.event)
		ticket_type = frappe.db.get_value("Event Ticket Type", ticket.ticket_type, "title")
		old_name, new_name, new_email = escape_html(old_name), escape_html(new_name), escape_html(new_email)

		send_message_email(
			title=_("Your ticket was transferred"),
			message=_(
				"<p>Hi {0},</p><p>Your {1} ticket for <strong>{2}</strong> is now with {3} ({4}).</p>"
				"<p>If you have any questions about this transfer, please contact us.</p>"
			).format(old_name, ticket_type, event.title, new_name, new_email),
			event=event,
			recipients=[old_email],
			subject=_("Your ticket for {0} has been transferred").format(event.title),
			delayed=False,
		)
		send_message_email(
			title=_("A ticket was transferred to you"),
			message=_(
				"<p>Hi {0},</p><p>A {1} ticket for <strong>{2}</strong> is now yours.</p>"
				"<p>Ticket ID: <strong>{3}</strong><br>Booking ID: <strong>{4}</strong></p>"
				"<p>Keep this email; you may need the ticket details at the entrance.</p>"
			).format(new_name, ticket_type, event.title, ticket.name, ticket.booking),
			event=event,
			recipients=[new_email],
			subject=_("Welcome! Your ticket for {0}").format(event.title),
			delayed=False,
		)
	except Exception as e:
		frappe.log_error(f"Failed to send ticket transfer emails for ticket {ticket_id}: {e!s}")
