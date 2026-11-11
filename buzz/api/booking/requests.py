import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from buzz.api.booking.details import ticket_type_titles
from buzz.api.booking.schemas import (
	PaymentLinkResponse,
	RegistrationRequestRow,
	RequestAnswer,
	RequestAttendee,
	RequestCounts,
)
from buzz.api.booking.services import verify_booking_access_token
from buzz.api.events.services import manageable_event
from buzz.ticketing.doctype.event_booking.registration_request import RegistrationRequest
from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import start_capacity_transaction
from buzz.ticketing.doctype.ticket_hold.ticket_hold import live_hold_expiry


class RequestService:
	"""Registration requests of one event, for anyone who can write its guest list."""

	def __init__(self, event: str):
		self.event = manageable_event(event, "guests")

	def requests(self, request_type: str) -> list[RegistrationRequestRow]:
		"""Every request of one type, open or decided, oldest first."""
		# ponytail: no paging, add when an event passes ~500 requests
		names = frappe.get_all(
			"Event Booking",
			filters={"event": self.event.name, "request_type": request_type, "docstatus": ("<", 2)},
			order_by="creation asc",
			pluck="name",
		)
		bookings = [frappe.get_doc("Event Booking", name) for name in names]
		titles = ticket_type_titles(bookings)
		positions = waitlist_positions(bookings)
		return [request_row(booking, titles, positions.get(booking.name)) for booking in bookings]

	def counts(self) -> RequestCounts:
		rows = frappe.get_all(
			"Event Booking",
			filters={"event": self.event.name, "docstatus": 0, "status": ("in", ("Requested", "Waitlisted"))},
			fields=["status", {"COUNT": "*", "as": "count"}],
			group_by="status",
		)
		by_status = {row.status: row.count for row in rows}
		return RequestCounts(
			pending=by_status.get("Requested", 0),
			waiting=by_status.get("Waitlisted", 0),
			seats_free=self.seats_free(),
		)

	def seats_free(self) -> dict[str, int]:
		ticket_types = frappe.get_all("Event Ticket Type", filters={"event": self.event.name}, pluck="name")
		seats = {}
		for name in ticket_types:
			ticket_type = frappe.get_cached_doc("Event Ticket Type", name)
			if ticket_type.has_waitlist_entries():
				seats[ticket_type.title] = ticket_type.get_remaining_tickets()
		return seats


def waitlist_positions(bookings: list) -> dict[str, int]:
	"""Rank of each waiting booking in the queue of its first ticket type."""
	queues: dict[str, int] = {}
	positions = {}
	for booking in bookings:
		if booking.status != "Waitlisted" or not booking.attendees:
			continue
		ticket_type = str(booking.attendees[0].ticket_type)
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


def request_row(booking, titles: dict[str, str], position: int | None = None) -> RegistrationRequestRow:
	return RegistrationRequestRow(
		name=booking.name,
		status=booking.status,
		request_type=booking.request_type,
		docstatus=booking.docstatus,
		position=position,
		offer_expires_at=live_hold_expiry(booking.hold_token)
		if booking.status == "Payment Pending"
		else None,
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
			for attendee in booking.attendees
		],
		answers=[RequestAnswer(label=field.label, value=field.value) for field in booking.additional_fields],
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
