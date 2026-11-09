import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from buzz.api.booking.details import ticket_type_titles
from buzz.api.booking.schemas import (
	PaymentLinkResponse,
	RegistrationRequestRow,
	RequestAnswer,
	RequestAttendee,
)
from buzz.api.booking.services import verify_booking_access_token
from buzz.api.events.services import manageable_event
from buzz.ticketing.doctype.event_booking.registration_request import OPEN_STATUSES, RegistrationRequest
from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import start_capacity_transaction


class RequestService:
	"""Registration requests of one event, for anyone who can write its guest list."""

	def __init__(self, event: str):
		self.event = manageable_event(event, "guests")

	def open_requests(self) -> list[RegistrationRequestRow]:
		# ponytail: no paging, add when an event passes ~500 requests
		names = frappe.get_all(
			"Event Booking",
			filters={"event": self.event.name, "docstatus": 0, "status": ("in", OPEN_STATUSES)},
			order_by="creation asc",
			pluck="name",
		)
		bookings = [frappe.get_doc("Event Booking", name) for name in names]
		titles = ticket_type_titles(bookings)
		return [request_row(booking, titles) for booking in bookings]


def managed_request(booking: str) -> RegistrationRequest:
	doc = frappe.get_doc("Event Booking", booking)
	manageable_event(doc.event, "guests")
	return RegistrationRequest(doc)


def own_request(booking: str, token: str | None) -> RegistrationRequest:
	owner = frappe.db.get_value("Event Booking", booking, "user")
	if not owner or (owner != frappe.session.user and not verify_booking_access_token(booking, token)):
		frappe.throw(_("You are not allowed to view this booking."), frappe.PermissionError)
	return RegistrationRequest(frappe.get_doc("Event Booking", booking))


def request_row(booking, titles: dict[str, str]) -> RegistrationRequestRow:
	return RegistrationRequestRow(
		name=booking.name,
		status=booking.status,
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
def get_requests(event: str) -> list[RegistrationRequestRow]:
	return RequestService(event).open_requests()


@frappe.whitelist(methods=["POST"])
def approve_request(booking: str) -> None:
	start_capacity_transaction()
	managed_request(booking).approve()


@frappe.whitelist(methods=["POST"])
def decline_request(booking: str, message: str | None = None) -> None:
	managed_request(booking).decline(message)


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=600)
def get_request_payment_link(booking: str, token: str | None = None) -> PaymentLinkResponse:
	start_capacity_transaction()
	return PaymentLinkResponse(payment_link=own_request(booking, token).payment_link())
