import frappe

from buzz.api.booking.downloads import send_file, ticket_pdf
from buzz.api.transactions.exceptions import TransactionNotFound
from buzz.api.transactions.services import ensure_transactions_access, transaction_names


def download_ticket(event: str, ticket: str) -> None:
	ensure_transactions_access(event)
	booking = frappe.db.get_value("Event Ticket", {"name": ticket, "docstatus": 1}, "booking")
	if not (booking and transaction_names(event, [["name", "=", booking]])):
		TransactionNotFound.throw()
	send_file(f"Ticket-{ticket}.pdf", ticket_pdf(ticket))
