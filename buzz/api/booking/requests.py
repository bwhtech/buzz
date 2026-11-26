import frappe
from frappe import _
from frappe.query_builder.functions import Count
from frappe.rate_limiter import rate_limit

from buzz.api.booking.schemas import (
	PaymentLinkResponse,
	RegistrationRequestRow,
	RequestAnswer,
	RequestAttendee,
	RequestCounts,
)
from buzz.api.booking.services import verify_booking_access_token
from buzz.api.events.exceptions import CannotManageEvent
from buzz.api.events.services import manageable_event
from buzz.permissions import has_section_permission
from buzz.ticketing.doctype.event_booking.registration_request import RegistrationRequest
from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import (
	remaining_for,
	sold_counts,
	start_capacity_transaction,
	waitlist_ticket_types,
)
from buzz.ticketing.doctype.ticket_hold.ticket_hold import held_quantities, live_hold_expiries

REQUEST_BOOKING_FIELDS = [
	"name",
	"status",
	"request_type",
	"docstatus",
	"hold_token",
	"buyer_name",
	"buyer_email",
	"total_amount",
	"currency",
	"creation",
]


class RequestService:
	"""Registration requests of one event, for anyone who can write its guest list."""

	def __init__(self, event: str):
		self.event = frappe.get_cached_doc("Buzz Event", str(event))
		self.event_id = str(self.event.name)
		if not has_section_permission(
			self.event_id, "guests", "write", frappe.session.user, team=self.event.team
		):
			CannotManageEvent.throw()

	def requests(self, request_type: str) -> list[RegistrationRequestRow]:
		"""Every request of one type, open or decided, oldest first."""
		# ponytail: no paging, add when an event passes ~500 requests
		booking_table = frappe.qb.DocType("Event Booking")
		bookings = (
			frappe.qb.from_(booking_table)
			.select(*(booking_table[field] for field in REQUEST_BOOKING_FIELDS))
			.where(
				(booking_table.event == self.event_id)
				& (booking_table.request_type == request_type)
				& (booking_table.docstatus < 2)
			)
			.orderby(booking_table.creation)
		).run(as_dict=True)
		if not bookings:
			return []
		names = [booking.name for booking in bookings]
		attendees_by_booking = request_attendees(names)
		answers_by_booking = request_answers(names)
		titles = request_ticket_type_titles(attendees_by_booking)
		expiries = live_hold_expiries(
			[
				booking.hold_token
				for booking in bookings
				if booking.status == "Payment Pending" and booking.hold_token
			]
		)
		positions = waitlist_positions(bookings, attendees_by_booking)
		return [
			request_row(
				booking,
				attendees_by_booking.get(booking.name, []),
				answers_by_booking.get(booking.name, []),
				titles,
				positions.get(booking.name),
				expiries.get(booking.hold_token) if booking.status == "Payment Pending" else None,
			)
			for booking in bookings
		]

	def counts(self) -> RequestCounts:
		booking_table = frappe.qb.DocType("Event Booking")
		rows = (
			frappe.qb.from_(booking_table)
			.select(booking_table.status, Count("*").as_("count"))
			.where(
				(booking_table.event == self.event_id)
				& (booking_table.docstatus == 0)
				& booking_table.status.isin(["Requested", "Waitlisted"])
			)
			.groupby(booking_table.status)
		).run(as_dict=True)
		by_status = {row.status: row.count for row in rows}
		waiting = by_status.get("Waitlisted", 0)
		return RequestCounts(
			pending=by_status.get("Requested", 0),
			waiting=waiting,
			seats_free=self.seats_free() if waiting else {},
		)

	def seats_free(self) -> dict[str, int]:
		queued_ids = waitlist_ticket_types(self.event_id)
		if not queued_ids:
			return {}
		tt = frappe.qb.DocType("Event Ticket Type")
		ticket_types = (
			frappe.qb.from_(tt)
			.select(tt.name, tt.title, tt.max_tickets_available)
			.where((tt.event == self.event_id) & tt.name.isin(list(queued_ids)))
		).run(as_dict=True)
		limited = [str(row.name) for row in ticket_types if row.max_tickets_available]
		sold = sold_counts(limited, event=self.event_id)
		held = held_quantities(limited)
		return {row.title: remaining_for(row, sold, held) for row in ticket_types}


def request_attendees(booking_names: list[str]) -> dict[str, list]:
	rows = frappe.get_all(
		"Event Booking Attendee",
		filters={"parenttype": "Event Booking", "parent": ("in", booking_names)},
		fields=["parent", "full_name", "first_name", "last_name", "email", "ticket_type"],
		order_by="parent asc, idx asc",
	)
	grouped: dict[str, list] = {}
	for row in rows:
		grouped.setdefault(row.parent, []).append(row)
	return grouped


def request_answers(booking_names: list[str]) -> dict[str, list]:
	rows = frappe.get_all(
		"Additional Field",
		filters={"parenttype": "Event Booking", "parent": ("in", booking_names)},
		fields=["parent", "label", "value"],
		order_by="parent asc, idx asc",
	)
	grouped: dict[str, list] = {}
	for row in rows:
		grouped.setdefault(row.parent, []).append(row)
	return grouped


def request_ticket_type_titles(attendees_by_booking: dict[str, list]) -> dict[str, str]:
	ids = {
		str(attendee.ticket_type)
		for attendees in attendees_by_booking.values()
		for attendee in attendees
		if attendee.ticket_type
	}
	if not ids:
		return {}
	rows = frappe.db.get_all(
		"Event Ticket Type", filters={"name": ("in", list(ids))}, fields=["name", "title"]
	)
	return {str(row.name): row.title for row in rows}


def waitlist_positions(bookings: list, attendees_by_booking: dict[str, list]) -> dict[str, int]:
	"""Rank of each waiting booking in the queue of its first ticket type."""
	queues: dict[str, int] = {}
	positions = {}
	for booking in bookings:
		attendees = attendees_by_booking.get(booking.name)
		if booking.status != "Waitlisted" or not attendees:
			continue
		ticket_type = str(attendees[0].ticket_type)
		queues[ticket_type] = queues.get(ticket_type, 0) + 1
		positions[booking.name] = queues[ticket_type]
	return positions


def managed_request(booking: str) -> RegistrationRequest:
	doc = frappe.get_doc("Event Booking", booking)
	manageable_event(doc.event, "guests")
	return RegistrationRequest(doc)


def own_request(booking: str, token: str | None) -> RegistrationRequest:
	owner = frappe.db.get_value("Event Booking", booking, "user")
	if not owner or (owner != frappe.session.user and not verify_booking_access_token(booking, token)):
		frappe.throw(_("You are not allowed to view this booking."), frappe.PermissionError)
	return RegistrationRequest(frappe.get_doc("Event Booking", booking))


def request_row(
	booking,
	attendees: list,
	answers: list,
	titles: dict[str, str],
	position: int | None = None,
	offer_expires_at=None,
) -> RegistrationRequestRow:
	return RegistrationRequestRow(
		name=booking.name,
		status=booking.status,
		request_type=booking.request_type,
		docstatus=booking.docstatus,
		position=position,
		offer_expires_at=offer_expires_at,
		buyer_name=booking.buyer_name,
		buyer_email=booking.buyer_email,
		total_amount=booking.total_amount,
		currency=booking.currency,
		requested_at=booking.creation,
		attendees=[
			RequestAttendee(
				full_name=attendee.full_name
				or " ".join(part for part in (attendee.first_name, attendee.last_name) if part),
				email=attendee.email,
				ticket_type=titles.get(str(attendee.ticket_type), str(attendee.ticket_type)),
			)
			for attendee in attendees
		],
		answers=[RequestAnswer(label=field.label, value=field.value) for field in answers],
	)


@frappe.whitelist()
def get_requests(event: str, request_type: str) -> list[RegistrationRequestRow]:
	return RequestService(event).requests(request_type)


@frappe.whitelist()
def get_request_counts(event: str) -> RequestCounts:
	return RequestService(event).counts()


@frappe.whitelist(methods=["POST"])
def approve_request(booking: str) -> None:
	start_capacity_transaction()
	managed_request(booking).approve()


@frappe.whitelist(methods=["POST"])
def decline_request(booking: str, message: str | None = None) -> None:
	managed_request(booking).decline(message)


@frappe.whitelist(methods=["POST"])
def reopen_request(booking: str) -> None:
	managed_request(booking).reopen()


@frappe.whitelist(methods=["POST"])
def revoke_request(booking: str) -> None:
	managed_request(booking).revoke()


@frappe.whitelist(methods=["POST"])
def resend_payment_link(booking: str) -> None:
	start_capacity_transaction()
	managed_request(booking).resend()


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=600)
def get_request_payment_link(booking: str, token: str | None = None) -> PaymentLinkResponse:
	start_capacity_transaction()
	return PaymentLinkResponse(payment_link=own_request(booking, token).payment_link())
