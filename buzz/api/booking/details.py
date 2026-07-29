import frappe
from frappe import _

from buzz.api.booking.schemas import (
	BookingConfirmationResponse,
	BookingDetailsResponse,
	ConfirmationBooking,
	ConfirmationEvent,
	ConfirmationTicket,
	ConfirmationVenue,
)
from buzz.api.booking.services import verify_booking_access_token
from buzz.api.tickets import windows

TICKET_FIELDS = [
	"name",
	"attendee_name",
	"attendee_email",
	"ticket_type.title as ticket_type",
	"qr_code",
]


def build_booking_confirmation(booking_id: str, token: str | None) -> BookingConfirmationResponse:
	# nosemgrep: frappe-semgrep-rules.rules.unchecked-frappe-permission-call -- return value checked below
	authorized = verify_booking_access_token(booking_id, token) or frappe.has_permission(
		"Event Booking", "read", doc=booking_id
	)
	if not authorized:
		frappe.throw(_("You are not allowed to view this booking."), frappe.PermissionError)

	booking_doc = frappe.get_cached_doc("Event Booking", booking_id)
	event_doc = frappe.get_cached_doc("Buzz Event", booking_doc.event)
	tickets = frappe.db.get_all("Event Ticket", filters={"booking": booking_id}, fields=TICKET_FIELDS)

	return BookingConfirmationResponse(
		event=ConfirmationEvent(
			title=event_doc.title,
			route=event_doc.route,
			start_date=event_doc.start_date,
			end_date=event_doc.end_date,
			start_time=event_doc.start_time,
			end_time=event_doc.end_time,
			short_description=event_doc.get("short_description"),
			free_event=event_doc.get("free_event"),
		),
		venue=get_confirmation_venue(event_doc.venue),
		booking=ConfirmationBooking(
			name=booking_doc.name,
			total_amount=booking_doc.total_amount,
			net_amount=booking_doc.net_amount,
			currency=booking_doc.currency,
			payment_status=booking_doc.payment_status,
			status=booking_doc.status,
			tax_amount=booking_doc.tax_amount,
			tax_label=booking_doc.tax_label,
			tax_percentage=booking_doc.tax_percentage,
			discount_amount=booking_doc.discount_amount,
			coupon_code=booking_doc.coupon_code,
		),
		tickets=[ConfirmationTicket(**ticket) for ticket in tickets],
	)


def get_confirmation_venue(venue_id: str | None) -> ConfirmationVenue | None:
	if not venue_id:
		return None
	venue_doc = frappe.get_cached_doc("Event Venue", venue_id)
	return ConfirmationVenue(name=venue_doc.name, address=venue_doc.get("address"))


def build_booking_details(booking_id: str) -> BookingDetailsResponse:
	booking_doc = frappe.get_cached_doc("Event Booking", booking_id)
	event_doc = frappe.get_cached_doc("Buzz Event", booking_doc.event)
	tickets = get_tickets_with_add_ons(booking_id, booking_doc.event)

	cancellation_request = frappe.db.get_value(
		"Ticket Cancellation Request",
		{"booking": booking_id},
		["name", "cancel_full_booking", "creation", "status", "docstatus"],
		as_dict=True,
	)

	return BookingDetailsResponse(
		doc=booking_doc,
		tickets=tickets,
		event=event_doc,
		venue=frappe.get_cached_doc("Event Venue", event_doc.venue) if event_doc.venue else None,
		can_transfer_ticket=windows.is_window_open(event_doc.name, windows.TRANSFER),
		can_change_add_ons=windows.is_window_open(event_doc.name, windows.ADD_ON_CHANGE),
		can_request_cancellation=windows.is_window_open(event_doc.name, windows.CANCELLATION),
		cancellation_request=cancellation_request,
		cancellation_requested_tickets=get_cancellation_requested_tickets(cancellation_request, tickets),
		cancelled_tickets=[ticket.name for ticket in tickets if ticket.docstatus == 2],
	)


def get_tickets_with_add_ons(booking_id: str, event_id: str) -> list:
	tickets = frappe.db.get_all(
		"Event Ticket",
		filters={"booking": booking_id},
		fields=[*TICKET_FIELDS, "event", "docstatus"],
	)
	add_ons = frappe.db.get_all(
		"Ticket Add-on Value",
		filters={"parent": ("in", [ticket.name for ticket in tickets])},
		fields=[
			"parent",
			"name",
			"add_on",
			"value",
			"add_on.title as add_on_title",
			"add_on.user_selects_option as user_selects_option",
		],
	)
	options_map = get_add_on_options_map(event_id)

	for ticket in tickets:
		ticket.add_ons = sorted(
			(
				{
					"id": add_on.name,
					"name": add_on.add_on,
					"title": add_on.add_on_title,
					"value": add_on.value,
					"user_selects_option": add_on.user_selects_option,
					"options": options_map.get(add_on.add_on, []),
				}
				for add_on in add_ons
				if add_on.parent == ticket.name
			),
			key=lambda add_on: add_on["title"],
		)
	return tickets


def get_add_on_options_map(event_id: str) -> dict:
	event_add_ons = frappe.db.get_all(
		"Ticket Add-on",
		filters={"event": event_id, "user_selects_option": True},
		fields=["name", "options"],
	)
	return {add_on.name: add_on.options.split("\n") if add_on.options else [] for add_on in event_add_ons}


def get_cancellation_requested_tickets(cancellation_request, tickets) -> list[str]:
	if not cancellation_request or cancellation_request.docstatus != 0:
		return []

	if cancellation_request.cancel_full_booking:
		return [ticket.name for ticket in tickets]

	requested = frappe.db.get_all(
		"Ticket Cancellation Item", filters={"parent": cancellation_request.name}, fields=["ticket"]
	)
	return [item.ticket for item in requested]
