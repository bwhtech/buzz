import frappe

from buzz.api.transactions import detail, downloads, services, summary
from buzz.api.transactions.schemas import TransactionDetail, TransactionsPage, TransactionSummary

PAGE_SIZE = 20


@frappe.whitelist()
def get_event_transactions(
	event: str,
	search: str | None = None,
	filters: str | None = None,
	order: str = "desc",
	start: int = 0,
	limit: int = PAGE_SIZE,
	name: str | None = None,
	status: str | None = None,
) -> TransactionsPage:
	"""One page of an event's paid-for bookings. `filters` is a JSON list of `[field, operator, value]`;
	`status` is one of `services.STATUS_FILTERS`."""
	return services.TransactionsList(event, search, filters, name, status).page(order, start, limit)


@frappe.whitelist()
def get_transaction(event: str, booking: str) -> TransactionDetail:
	return detail.TransactionDetailBuilder(event, booking).detail()


@frappe.whitelist()
def download_ticket(event: str, ticket: str) -> None:
	"""Responds with the ticket's PDF, as `Ticket-<name>.pdf`."""
	downloads.download_ticket(event, ticket)


@frappe.whitelist()
def get_transaction_summary(event: str) -> TransactionSummary:
	return summary.transaction_summary(event)
