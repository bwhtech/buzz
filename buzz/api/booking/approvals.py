from typing import Literal

import frappe
from frappe import _

from buzz.api.booking.details import ticket_type_titles
from buzz.api.booking.exceptions import BookingNotPending, CannotWithdrawBooking
from buzz.api.booking.schemas import (
	AffectedRequestsResponse,
	ApproveBookingsResponse,
	DeclineBookingsResponse,
	FailedApproval,
	PendingAnswer,
	PendingAttendee,
	PendingBooking,
	PendingBookingsResponse,
	SetApprovalResponse,
)
from buzz.api.booking.services import verify_booking_access_token
from buzz.api.events.services import manageable_event
from buzz.ticketing.approval import PENDING_APPROVAL, approval_ticket_types
from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import start_capacity_transaction


class ApprovalService:
	"""Approval requests of one event, for anyone who can write its guest list."""

	def __init__(self, event: str):
		self.event = manageable_event(event, "guests")

	def pending_names(self) -> list[str]:
		filters = {**PENDING_APPROVAL, "event": self.event.name}
		return frappe.get_all("Event Booking", filters=filters, order_by="creation asc", pluck="name")

	def pending_booking(self, name: str):
		booking = frappe.get_doc("Event Booking", name)
		if str(booking.event) != str(self.event.name) or not is_pending_request(booking):
			BookingNotPending.throw()
		return booking

	def pending_bookings(self) -> PendingBookingsResponse:
		bookings = [frappe.get_doc("Event Booking", name) for name in self.pending_names()]
		titles = ticket_type_titles(bookings)
		declined_users = self.previously_declined_users()
		return PendingBookingsResponse(
			total=len(bookings),
			bookings=[
				pending_booking_row(booking, titles, booking.user in declined_users) for booking in bookings
			],
		)

	def previously_declined_users(self) -> set[str]:
		filters = {"event": self.event.name, "requires_approval": 1, "status": "Rejected"}
		return set(frappe.get_all("Event Booking", filters=filters, pluck="user"))

	def approve(self, names: list[str]) -> ApproveBookingsResponse:
		start_capacity_transaction()
		result = ApproveBookingsResponse(approved=[], failed=[])
		for name in names:
			error = self.try_approve(name)
			if error:
				result.failed.append(FailedApproval(booking=name, error=error))
			else:
				result.approved.append(name)
		return result

	def try_approve(self, name: str) -> str | None:
		"""The reason the request could not be approved, or None once it was."""
		frappe.db.savepoint("approve_request")
		try:
			self.pending_booking(name).approve_request()
		except frappe.ValidationError as error:
			frappe.db.rollback(save_point="approve_request")
			frappe.clear_messages()
			return str(error)

	def decline(self, names: list[str], message: str | None) -> DeclineBookingsResponse:
		reason = (message or "").strip() or None
		for name in names:
			self.pending_booking(name).decline_request(reason)
		return DeclineBookingsResponse(declined=names)

	def released_requests(self, ticket_type: str | None) -> list[str]:
		"""Pending requests that stop needing approval once it is turned off for
		`ticket_type`, or for the whole event when that is None."""
		if ticket_type is not None and self.event.requires_approval:
			return []
		still_required = approval_ticket_types(self.event.name) - {str(ticket_type)}
		types_by_booking = self.ticket_types_by_pending_booking()
		return [
			name
			for name, types in types_by_booking.items()
			if not types & still_required and (ticket_type is None or str(ticket_type) in types)
		]

	def ticket_types_by_pending_booking(self) -> dict[str, set[str]]:
		names = self.pending_names()
		rows = frappe.db.get_all(
			"Event Booking Attendee", filters={"parent": ("in", names)}, fields=["parent", "ticket_type"]
		)
		types = {name: set() for name in names}
		for row in rows:
			types[row.parent].add(str(row.ticket_type))
		return types

	def set_approval(
		self, enabled: bool, ticket_type: str | None, pending_action: Literal["keep", "approve", "decline"]
	) -> SetApprovalResponse:
		setting = self.approval_setting(ticket_type)
		released = [] if enabled else self.released_requests(ticket_type)
		setting.requires_approval = int(enabled)
		setting.flags.ignore_permissions = True
		setting.save()
		return self.apply_pending_action(released, pending_action)

	def approval_setting(self, ticket_type: str | None):
		"""The document holding the switch: the event, or one of its ticket types."""
		if not ticket_type:
			return self.event
		ticket_type_doc = frappe.get_doc("Event Ticket Type", ticket_type)
		if str(ticket_type_doc.event) != str(self.event.name):
			frappe.throw(_("This ticket type belongs to another event"))
		return ticket_type_doc

	def apply_pending_action(self, released: list[str], action: str) -> SetApprovalResponse:
		result = SetApprovalResponse(approved=0, failed=0, declined=0)
		if not released:
			return result
		if action == "approve":
			approval = self.approve(released)
			result.approved, result.failed = len(approval.approved), len(approval.failed)
		elif action == "decline":
			result.declined = len(self.decline(released, None).declined)
		return result


def pending_booking_row(booking, titles: dict[str, str], previously_declined: bool) -> PendingBooking:
	return PendingBooking(
		name=booking.name,
		buyer_name=booking.buyer_name,
		buyer_email=booking.buyer_email,
		requested_at=booking.creation,
		previously_declined=previously_declined,
		attendees=[
			PendingAttendee(
				full_name=attendee.full_name
				or " ".join(part for part in (attendee.first_name, attendee.last_name) if part),
				email=attendee.email,
				ticket_type=titles.get(str(attendee.ticket_type), str(attendee.ticket_type)),
			)
			for attendee in booking.attendees
		],
		answers=[PendingAnswer(label=field.label, value=field.value) for field in booking.additional_fields],
	)


def is_pending_request(booking) -> bool:
	return booking.docstatus == 0 and bool(booking.requires_approval) and booking.status == "Approval Pending"


def withdraw_request(name: str, token: str | None) -> None:
	booking = frappe.get_doc("Event Booking", name)
	if booking.user != frappe.session.user and not verify_booking_access_token(name, token):
		CannotWithdrawBooking.throw()
	if not is_pending_request(booking):
		BookingNotPending.throw()
	booking.discard_as("Withdrawn")


@frappe.whitelist()
def get_pending_bookings(event: str) -> PendingBookingsResponse:
	return ApprovalService(event).pending_bookings()


@frappe.whitelist(methods=["POST"])
def approve_bookings(event: str, bookings: list[str]) -> ApproveBookingsResponse:
	return ApprovalService(event).approve(bookings)


@frappe.whitelist(methods=["POST"])
def decline_bookings(event: str, bookings: list[str], message: str | None = None) -> DeclineBookingsResponse:
	return ApprovalService(event).decline(bookings, message)


@frappe.whitelist()
def get_affected_requests(event: str, ticket_type: str | None = None) -> AffectedRequestsResponse:
	return AffectedRequestsResponse(count=len(ApprovalService(event).released_requests(ticket_type)))


@frappe.whitelist(methods=["POST"])
def set_approval(
	event: str,
	enabled: bool,
	ticket_type: str | None = None,
	pending_action: Literal["keep", "approve", "decline"] = "keep",
) -> SetApprovalResponse:
	return ApprovalService(event).set_approval(enabled, ticket_type, pending_action)


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
def withdraw_booking(booking: str, token: str | None = None) -> None:
	withdraw_request(booking, token)
