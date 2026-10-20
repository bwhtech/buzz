from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.utils import cstr, format_date, format_time, today

from buzz.api.checkin.exceptions import (
	AlreadyCheckedIn,
	NotCheckedIn,
	TicketCancelled,
	TicketNotFound,
	TicketRefunded,
)
from buzz.api.checkin.schemas import (
	CheckinEvent,
	CheckinResponse,
	PaymentDetails,
	TicketAddOn,
	TicketCheckinDetails,
)
from buzz.api.exceptions import NotPermitted
from buzz.permissions import CHECKIN_ROLES, EDIT, can_check_in, is_unrestricted
from buzz.ticketing.doctype.event_booking_refund.event_booking_refund import get_committed_tickets

if TYPE_CHECKING:
	from buzz.events.doctype.buzz_event.buzz_event import BuzzEvent
	from buzz.events.doctype.event_check_in.event_check_in import EventCheckIn
	from buzz.ticketing.doctype.event_ticket.event_ticket import EventTicket

CANCELLED = 2


def ensure_can_check_in(event: str) -> None:
	if not can_check_in(event, frappe.session.user):
		NotPermitted.throw()


def checkin_events() -> list[CheckinEvent]:
	"""Events not yet over, on the teams the user works the front desk for, or that they collaborate on."""
	filters = {"is_published": 1, "end_date": [">=", today()]}
	user = frappe.session.user
	or_filters = None
	if not is_unrestricted(user):
		teams = frappe.get_all(
			"Buzz Team Membership",
			filters={"user": user, "enabled": 1, "team_role": ["in", list(CHECKIN_ROLES)]},
			pluck="team",
		)
		collaborating = frappe.get_all(
			"Buzz Event Collaborator",
			filters={"user": user, "status": "Accepted", "guests_access": EDIT},
			pluck="event",
		)
		or_filters = [
			[field, "in", names] for field, names in (("team", teams), ("name", collaborating)) if names
		]
		if not or_filters:
			return []

	rows = frappe.get_all(
		"Buzz Event",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "title", "start_date", "start_time", "end_date", "end_time"],
		order_by="start_date asc",
		ignore_permissions=True,
	)
	return [CheckinEvent(**{**row, "name": str(row.name)}) for row in rows]


class CheckinService:
	"""Front-desk check-in for a single ticket, by a team member at Frontdesk or above."""

	def __init__(self, ticket_id: str):
		if not frappe.db.exists("Event Ticket", ticket_id):
			TicketNotFound.throw()

		self.ticket_id = ticket_id
		self.date = today()
		# Both endpoints route through here, so one team check covers them.
		ensure_can_check_in(self.ticket.event)

	@property
	def ticket(self) -> "EventTicket":
		return frappe.get_cached_doc("Event Ticket", self.ticket_id)

	@property
	def event(self) -> "BuzzEvent":
		return frappe.get_cached_doc("Buzz Event", self.ticket.event)

	def validate(self) -> CheckinResponse:
		self.ensure_checkin_allowed()
		return CheckinResponse(
			message=_("Valid ticket ready for check-in"),
			ticket=self.ticket_details(),
			payment_details=self.payment_details(),
		)

	def checkin(self) -> CheckinResponse:
		self.ensure_checkin_allowed()
		checkin_doc = self.record_checkin()

		return CheckinResponse(
			message=_("Successfully checked in {attendee_name} for {checkin_date}").format(
				attendee_name=self.ticket.attendee_name,
				checkin_date=frappe.format(self.date, {"fieldtype": "Date"}),
			),
			ticket=self.ticket_details(
				is_checked_in=True,
				check_in_time=checkin_doc.creation,
				check_in_date=self.date,
			),
		)

	def ensure_checkin_allowed(self) -> None:
		if self.ticket.docstatus == CANCELLED:
			TicketCancelled.throw()

		# A refund that has not failed is money on its way back to the attendee,
		# whether or not it has got as far as cancelling the ticket.
		if self.ticket.booking and self.ticket_id in get_committed_tickets(self.ticket.booking):
			TicketRefunded.throw()

		existing = self.todays_checkin()
		if existing:
			creation = frappe.db.get_value("Event Check In", existing, "creation")
			AlreadyCheckedIn.throw(checked_in_at=f"{format_date(creation)} at {format_time(creation)}")

	def undo_checkin(self) -> CheckinResponse:
		existing = self.todays_checkin()
		if not existing:
			NotCheckedIn.throw()

		# Cancelled rather than deleted, so the record of the mistaken check-in stays.
		checkin_doc = frappe.get_doc("Event Check In", existing)
		checkin_doc.flags.ignore_permissions = True
		checkin_doc.cancel()
		return CheckinResponse(
			message=_("Undid the check-in for {attendee_name}").format(
				attendee_name=self.ticket.attendee_name
			),
			ticket=self.ticket_details(),
		)

	def todays_checkin(self) -> str | None:
		return frappe.db.exists(
			"Event Check In", {"ticket": self.ticket_id, "date": self.date, "docstatus": 1}
		)

	def record_checkin(self) -> "EventCheckIn":
		checkin_doc = frappe.new_doc("Event Check In")
		checkin_doc.ticket = self.ticket_id
		checkin_doc.date = self.date
		checkin_doc.insert(ignore_permissions=True)
		checkin_doc.submit()
		return checkin_doc

	def ticket_details(self, **checkin_state) -> TicketCheckinDetails:
		ticket_type = (
			frappe.get_cached_value("Event Ticket Type", self.ticket.ticket_type, "title")
			if self.ticket.ticket_type
			else None
		)

		return TicketCheckinDetails(
			id=self.ticket.name,
			attendee_name=self.ticket.attendee_name,
			attendee_email=self.ticket.attendee_email,
			event_title=self.event.title,
			ticket_type=ticket_type or self.ticket.ticket_type,
			venue=self.event.get_venue_name(),
			start_date=self.event.start_date,
			start_time=self.event.start_time,
			end_date=self.event.end_date,
			end_time=self.event.end_time,
			is_checked_in=checkin_state.get("is_checked_in", False),
			check_in_time=checkin_state.get("check_in_time"),
			check_in_date=checkin_state.get("check_in_date"),
			booking_id=self.ticket.booking,
			add_ons=self.add_ons(),
		)

	def add_ons(self) -> list[TicketAddOn]:
		rows = frappe.db.get_all(
			"Ticket Add-on Value",
			filters={"parent": self.ticket_id},
			fields=[
				"add_on",
				"add_on.title as add_on_title",
				"add_on.user_selects_option as add_on_selects_option",
				"value",
				"price",
				"currency",
			],
		)
		return [TicketAddOn(**row) for row in rows]

	def payment_details(self) -> PaymentDetails | None:
		if not self.ticket.booking:
			return None

		payments = frappe.db.get_all(
			"Event Payment",
			filters={
				"reference_doctype": "Event Booking",
				"reference_docname": self.ticket.booking,
				"payment_received": 1,
			},
			fields=["name", "amount", "currency"],
			limit=1,
		)
		if not payments:
			return None

		payment = payments[0]
		# Event Payment is named by autoincrement, so its name arrives as an int.
		return PaymentDetails(name=cstr(payment.name), amount=payment.amount, currency=payment.currency)
