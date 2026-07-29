from typing import TYPE_CHECKING

import frappe

from buzz.api.tickets import windows
from buzz.api.tickets.emails import send_ticket_transfer_emails
from buzz.api.tickets.exceptions import (
	AddOnChangeWindowClosed,
	AddOnValueNotFound,
	CancellationAlreadyRequested,
	CancellationNotPermitted,
	CancellationWindowClosed,
	TicketNotAccessible,
	TicketNotFound,
	TicketNotInBooking,
	TransferNotPermitted,
	TransferWindowClosed,
)
from buzz.api.tickets.schemas import TicketAddOnDetail, TicketDetailsResponse

if TYPE_CHECKING:
	from buzz.ticketing.doctype.event_ticket.event_ticket import EventTicket


class TicketService:
	"""Read or act on one Event Ticket on behalf of its attendee."""

	def __init__(self, ticket_id: str):
		self.ticket_id = ticket_id

	@property
	def ticket(self) -> "EventTicket":
		return frappe.get_cached_doc("Event Ticket", self.ticket_id)

	def details(self) -> TicketDetailsResponse:
		ticket = self.ticket
		if frappe.session.user != "Administrator" and ticket.attendee_email != frappe.session.user:
			TicketNotAccessible.throw()

		event_id = ticket.event
		zoom = self.zoom_registration()
		return TicketDetailsResponse(
			doc=ticket,
			add_ons=self.add_on_details(event_id),
			event=frappe.get_cached_doc("Buzz Event", event_id),
			booking=self.booking_owned_by_user(),
			ticket_type=frappe.get_cached_doc("Event Ticket Type", ticket.ticket_type),
			can_transfer_ticket=windows.is_window_open(event_id, windows.TRANSFER),
			can_change_add_ons=windows.is_window_open(event_id, windows.ADD_ON_CHANGE),
			can_request_cancellation=windows.is_window_open(event_id, windows.CANCELLATION),
			zoom_join_url=zoom.get("join_url"),
			zoom_reference_doctype=zoom.get("reference_doctype"),
			zoom_reference_name=zoom.get("reference_name"),
		)

	def add_on_details(self, event_id: str) -> list[TicketAddOnDetail]:
		add_ons = frappe.db.get_all(
			"Ticket Add-on Value",
			filters={"parent": self.ticket_id},
			fields=[
				"name",
				"add_on",
				"add_on.title as add_on_title",
				"value",
				"price",
				"currency",
				"add_on.user_selects_option as user_selects_option",
			],
		)
		options = self.selectable_options(event_id)
		return [
			TicketAddOnDetail(
				id=add_on.name,
				name=add_on.add_on,
				title=add_on.add_on_title,
				value=add_on.value,
				price=add_on.price,
				currency=add_on.currency,
				user_selects_option=add_on.user_selects_option,
				options=options.get(add_on.add_on, []),
			)
			for add_on in add_ons
		]

	def selectable_options(self, event_id: str) -> dict[str, list[str]]:
		event_add_ons = frappe.db.get_all(
			"Ticket Add-on",
			filters={"event": event_id, "user_selects_option": True},
			fields=["name", "options"],
		)
		return {add_on.name: add_on.options.split("\n") if add_on.options else [] for add_on in event_add_ons}

	def booking_owned_by_user(self):
		"""The booking, but only for the user who made it — an attendee sees None."""
		booking_id = self.ticket.booking
		if not booking_id:
			return None

		booking = frappe.get_cached_doc("Event Booking", booking_id)
		return booking if booking.owner == frappe.session.user else None

	def zoom_registration(self) -> dict:
		registration_id = self.ticket.get("zoom_session_registration")
		if not registration_id:
			return {}

		return (
			frappe.db.get_value(
				"Zoom Session Registration",
				registration_id,
				["join_url", "reference_doctype", "reference_name"],
				as_dict=True,
			)
			or {}
		)

	def transfer(self, new_first_name: str, new_last_name: str, new_email: str) -> None:
		if not frappe.db.exists("Event Ticket", self.ticket_id):
			TicketNotFound.throw()

		ticket = frappe.get_doc("Event Ticket", self.ticket_id)
		if not self.may_transfer(ticket):
			TransferNotPermitted.throw()

		if not windows.is_window_open(ticket.event, windows.TRANSFER):
			TransferWindowClosed.throw()

		old_name, old_email = ticket.attendee_name, ticket.attendee_email
		ticket.first_name = new_first_name
		ticket.last_name = new_last_name
		ticket.attendee_email = new_email
		ticket.save(ignore_permissions=True)

		new_name = f"{new_first_name} {new_last_name}".strip()
		send_ticket_transfer_emails(ticket.name, old_name, old_email, new_name, new_email)

	def may_transfer(self, ticket: "EventTicket") -> bool:
		if ticket.attendee_email == frappe.session.user:
			return True
		if frappe.db.get_value("Event Booking", ticket.booking, "user") == frappe.session.user:
			return True
		return bool(frappe.has_permission("Event Ticket", "write", ticket))


def change_add_on_preference(add_on_id: str, new_value: str) -> None:
	if not frappe.db.exists("Ticket Add-on Value", add_on_id):
		AddOnValueNotFound.throw()

	add_on_value = frappe.get_cached_doc("Ticket Add-on Value", add_on_id)
	ticket = frappe.get_cached_doc("Event Ticket", add_on_value.parent)

	if not windows.is_window_open(ticket.event, windows.ADD_ON_CHANGE):
		AddOnChangeWindowClosed.throw()

	frappe.db.set_value("Ticket Add-on Value", add_on_id, "value", new_value)


def create_cancellation_request(booking_id: str, ticket_ids: list | None = None) -> None:
	booking = frappe.get_cached_doc("Event Booking", booking_id)

	if booking.user != frappe.session.user and not frappe.has_permission("Event Booking", "write", booking):
		CancellationNotPermitted.throw()

	if not windows.is_window_open(booking.event, windows.CANCELLATION):
		CancellationWindowClosed.throw()

	if frappe.db.exists("Ticket Cancellation Request", {"booking": booking_id, "docstatus": 0}):
		CancellationAlreadyRequested.throw()

	booked_ticket_count = frappe.db.count("Event Ticket", {"booking": booking_id})
	request = frappe.new_doc("Ticket Cancellation Request")
	request.booking = booking_id
	request.cancel_full_booking = not ticket_ids or len(ticket_ids) == booked_ticket_count

	if not request.cancel_full_booking:
		for ticket_id in ticket_ids:
			if frappe.db.get_value("Event Ticket", ticket_id, "booking") != booking_id:
				TicketNotInBooking.throw(ticket_id=ticket_id, booking_id=booking_id)
			request.append("tickets", {"ticket": ticket_id})

	request.insert(ignore_permissions=True)


def create_add_on_doc(attendee_name: str, add_ons: list[dict]):
	for add_on in add_ons:
		add_on["currency"] = frappe.db.get_value("Ticket Add-on", add_on["add_on"], "currency")

	return frappe.get_doc(
		{"doctype": "Attendee Ticket Add-on", "add_ons": add_ons, "attendee_name": attendee_name}
	).insert(ignore_permissions=True)
