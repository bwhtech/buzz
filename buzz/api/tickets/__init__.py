import frappe

from buzz.api.tickets import services
from buzz.api.tickets.schemas import TicketDetailsResponse


@frappe.whitelist()
def get_ticket_details(ticket_id: str) -> TicketDetailsResponse:
	return services.TicketService(ticket_id).details()


@frappe.whitelist(methods=["POST"])
def transfer_ticket(ticket_id: str, new_first_name: str, new_last_name: str, new_email: str) -> None:
	services.TicketService(ticket_id).transfer(new_first_name, new_last_name, new_email)


@frappe.whitelist(methods=["POST"])
def change_add_on_preference(add_on_id: str, new_value: str) -> None:
	services.change_add_on_preference(add_on_id, new_value)


@frappe.whitelist(methods=["POST"])
def create_cancellation_request(booking_id: str, ticket_ids: list | None = None) -> None:
	services.create_cancellation_request(booking_id, ticket_ids)
