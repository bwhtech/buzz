import frappe
from frappe import _
from frappe.utils import flt

from buzz.api.booking.schemas import (
	BookingConfirmationResponse,
	BookingDetailsResponse,
	BookingLine,
	BookingSummary,
	ConfirmationBooking,
	ConfirmationEvent,
	ConfirmationTicket,
	ConfirmationVenue,
)
from buzz.api.booking.services import OFFLINE_PAYMENT_METHOD, verify_booking_access_token
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
	ensure_booking_is_readable(booking_doc)
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


def ensure_booking_is_readable(booking_doc) -> None:
	if booking_doc.user == frappe.session.user:
		return
	if not frappe.has_permission("Event Booking", "read", doc=booking_doc):
		frappe.throw(_("You are not allowed to view this booking."), frappe.PermissionError)


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


def build_my_booking_summaries(event: str) -> list[BookingSummary]:
	"""The session user's own bookings for one event, newest first.

	The `user` filter is the scope, and the permission query still applies on top of it —
	nothing here runs with ignore_permissions. A draft stays in so an offline booking
	awaiting verification is visible; a cancelled one drops out.
	"""
	names = frappe.get_all(
		"Event Booking",
		filters={"event": event, "user": frappe.session.user, "docstatus": ("!=", 2)},
		order_by="creation desc",
		pluck="name",
	)
	bookings = [frappe.get_cached_doc("Event Booking", name) for name in names]
	titles = ticket_type_titles(bookings)
	add_ons = add_on_values(bookings)
	return [summarize_booking(booking, titles, add_ons) for booking in bookings]


def build_booking_summary(booking_id: str) -> BookingSummary:
	"""One booking as a receipt, for its buyer or for anyone holding a ticket in it.

	Read permission on Event Booking covers the buyer and the event's team. It does not
	cover an attendee somebody else booked for — and they hold the ticket this receipt
	explains, so they are let through here rather than by widening the doctype's rule.
	"""
	# nosemgrep: frappe-semgrep-rules.rules.unchecked-frappe-permission-call -- return value checked below
	if not frappe.has_permission("Event Booking", "read", doc=booking_id) and not holds_ticket(booking_id):
		frappe.throw(_("You are not allowed to view this booking."), frappe.PermissionError)

	booking = frappe.get_cached_doc("Event Booking", booking_id)
	return summarize_booking(booking, ticket_type_titles([booking]), add_on_values([booking]))


def holds_ticket(booking_id: str) -> bool:
	"""Whether the session user is an attendee on this booking."""
	return bool(
		frappe.db.exists(
			"Event Ticket",
			{"booking": booking_id, "attendee_email": frappe.session.user, "docstatus": 1},
		)
	)


def ticket_type_titles(bookings: list) -> dict[str, str]:
	"""Titles for every ticket type across the bookings, in one query.

	Ticket types autoname to integers and arrive off an attendee row as strings, so both
	sides of the lookup are cast.
	"""
	ids = {attendee.ticket_type for booking in bookings for attendee in booking.attendees}
	if not ids:
		return {}

	# db.get_all: the bookings themselves are already permission-checked, and a title is
	# all that is read.
	rows = frappe.db.get_all(
		"Event Ticket Type", filters={"name": ("in", list(ids))}, fields=["name", "title"]
	)
	return {str(row.name): row.title for row in rows}


def add_on_values(bookings: list) -> dict[str, list]:
	"""Add-on rows bought across the bookings, grouped by the attendee row that holds them."""
	parents = {attendee.add_ons for booking in bookings for attendee in booking.attendees if attendee.add_ons}
	if not parents:
		return {}

	rows = frappe.db.get_all(
		"Ticket Add-on Value",
		filters={"parent": ("in", list(parents))},
		fields=["parent", "add_on", "add_on.title as title", "price"],
	)

	grouped = {}
	for row in rows:
		grouped.setdefault(row.parent, []).append(row)
	return grouped


def summarize_booking(booking, titles: dict[str, str], add_ons: dict[str, list]) -> BookingSummary:
	return BookingSummary(
		name=booking.name,
		# A guest checkout runs as Administrator, so `user` is the buyer of record.
		booked_by=booking.user or booking.owner,
		status=booking.status,
		payment_status=booking.payment_status,
		payment_method=booking.offline_payment_method or booking.payment_method,
		is_offline=booking.payment_method == OFFLINE_PAYMENT_METHOD,
		currency=booking.currency,
		booked_on=booking.creation,
		lines=build_lines(booking, titles, add_ons),
		net_amount=flt(booking.net_amount),
		discount_amount=flt(booking.discount_amount),
		coupon_code=booking.coupon_code,
		tax_amount=flt(booking.tax_amount),
		tax_label=booking.tax_label,
		tax_percentage=flt(booking.tax_percentage),
		total_amount=flt(booking.total_amount),
	)


def build_lines(booking, titles: dict[str, str], add_ons: dict[str, list]) -> list[BookingLine]:
	"""One line per ticket type, with the add-ons bought against it beneath.

	ponytail: line amounts are the stored attendee amounts. A Free Tickets coupon zeroes
	those after the subtotal has already counted them, so under that coupon the lines sum
	to less than `net_amount` and the discount line makes up the difference.
	"""
	lines: dict[str, BookingLine] = {}
	# Two add-ons of one event may carry the same title, so the sub-lines are keyed by
	# add-on id and the title is only ever displayed.
	sub_lines: dict[tuple[str, str], BookingLine] = {}
	for attendee in booking.attendees:
		key = str(attendee.ticket_type)
		line = lines.setdefault(key, BookingLine(label=titles.get(key, key), quantity=0, amount=0))
		line.quantity += 1
		line.amount += flt(attendee.amount)
		fold_add_ons(line, sub_lines, key, add_ons.get(attendee.add_ons, []))
	return list(lines.values())


def fold_add_ons(line: BookingLine, sub_lines: dict, ticket_type: str, rows: list) -> None:
	"""Fold one attendee's add-ons into their ticket type's line, one entry per add-on."""
	for row in rows:
		add_on = sub_lines.get((ticket_type, str(row.add_on)))
		if not add_on:
			add_on = BookingLine(label=row.title, quantity=0, amount=0)
			line.add_ons.append(add_on)
			sub_lines[(ticket_type, str(row.add_on))] = add_on
		add_on.quantity += 1
		add_on.amount += flt(row.price)
