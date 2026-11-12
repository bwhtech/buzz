from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, get_url, now_datetime

from buzz.api.booking.exceptions import RequestAlreadyOpen, RequestNotOpen
from buzz.payments import get_payment_link_for_booking
from buzz.permissions import has_section_permission
from buzz.ticketing.doctype.ticket_hold.ticket_hold import (
	PAYMENT_HOLD_MINUTES,
	live_hold_expiry,
	release_hold,
)

if TYPE_CHECKING:
	from buzz.ticketing.doctype.event_booking.event_booking import EventBooking

REQUEST_STATUSES = ("Requested", "Waitlisted")
OPEN_STATUSES = (*REQUEST_STATUSES, "Payment Pending")
STATUS_OF_TYPE = {"Approval": "Requested", "Waitlist": "Waitlisted"}
DEFAULT_PAYMENT_OFFER_HOURS = 48


def payment_offer_hours(event: str) -> int:
	return (
		cint(frappe.get_cached_value("Buzz Event", event, "payment_offer_hours"))
		or DEFAULT_PAYMENT_OFFER_HOURS
	)


class RegistrationRequest:
	"""A draft booking an organizer approves or declines before it is confirmed."""

	def __init__(self, booking: "EventBooking"):
		self.booking = booking

	@property
	def event_title(self) -> str:
		return frappe.get_cached_value("Buzz Event", self.booking.event, "title")

	def start(self) -> None:
		"""Turn a new booking into a request when its tickets need the organizer."""
		status = self.initial_status()
		if status:
			self.booking.status = status
			self.booking.request_type = "Waitlist" if status == "Waitlisted" else "Approval"

	def initial_status(self) -> str | None:
		"""The request status a new booking starts in, or None when it books straight away.
		Organizers skip approval, but a sold-out ticket type queues them like anyone else."""
		quantities = self.booking.ticket_quantities()
		ticket_types = self.ticket_types()
		hold_token = self.booking.hold_token
		if any(row.joins_waitlist(quantities[str(row.name)], hold_token) for row in ticket_types):
			return "Waitlisted"
		if has_section_permission(self.booking.event, "guests", "create", frappe.session.user):
			return None
		if any(ticket_type.needs_approval for ticket_type in ticket_types):
			return "Requested"
		return None

	def ticket_types(self) -> list:
		return [frappe.get_cached_doc("Event Ticket Type", name) for name in self.booking.ticket_quantities()]

	def validate_no_open_request(self) -> None:
		filters = {
			"event": self.booking.event,
			"user": self.booking.user,
			"docstatus": 0,
			"name": ("!=", self.booking.name or ""),
		}
		if frappe.db.exists("Event Booking", {**filters, "status": ("in", OPEN_STATUSES)}):
			RequestAlreadyOpen.throw()

	def approve(self) -> None:
		"""Leaving the request status makes `validate` reprice the booking. The organizer's
		decision overrides capacity, so a waitlist entry can be let in while sold out."""
		self.validate_is_request()
		self.booking.flags.ignore_permissions = True
		self.booking.flags.organizer_override = True
		if not self.booking.total_amount:
			self.booking.status = "Confirmed"
			self.booking.submit()
			return
		self.booking.status = "Payment Pending"
		self.booking.save()
		self.booking.hold_draft_tickets()
		self.send_approved_email()

	def send_approved_email(self) -> None:
		self.send_email(
			"booking_request_approved",
			_("You're approved for {0}: pay to confirm your spot").format(self.event_title),
			pay_url=get_url(self.booking_page()),
			hours=payment_offer_hours(self.booking.event),
		)

	def resend(self) -> None:
		"""Email the payment link again. A lapsed offer is held again first, past capacity if need be."""
		self.validate_is_payment_pending()
		if not live_hold_expiry(self.booking.hold_token):
			self.booking.flags.organizer_override = True
			self.booking.flags.ignore_permissions = True
			self.booking.save()
			self.booking.hold_draft_tickets()
		self.send_approved_email()

	def revoke(self) -> None:
		"""Take back an approval the guest has not paid for; their seats go back on sale."""
		self.validate_is_payment_pending()
		release_hold(self.booking.hold_token)
		self.set_status(STATUS_OF_TYPE[self.booking.request_type or "Approval"])

	def reopen(self) -> None:
		"""Put a declined request back in the queue."""
		if (
			self.booking.docstatus != 0
			or self.booking.status != "Rejected"
			or self.booking.request_type not in STATUS_OF_TYPE
		):
			RequestNotOpen.throw()
		self.validate_no_open_request()
		self.set_status(STATUS_OF_TYPE[self.booking.request_type])

	def set_status(self, status: str) -> None:
		"""Saved rather than set, so the change shows in the booking's activity."""
		self.booking.status = status
		self.booking.flags.ignore_permissions = True
		self.booking.flags.organizer_override = True
		self.booking.save()

	def validate_is_payment_pending(self) -> None:
		if self.booking.docstatus != 0 or self.booking.status != "Payment Pending":
			RequestNotOpen.throw()

	def payment_link(self) -> str:
		self.validate_is_payment_pending()
		if not live_hold_expiry(self.booking.hold_token):
			self.hold_again()
		return get_payment_link_for_booking(self.booking.name, redirect_to=self.booking_page())

	def hold_again(self) -> None:
		"""The offer lapsed: `save` checks the tickets are still there, then they are held again."""
		self.booking.flags.ignore_permissions = True
		self.booking.save()
		self.booking.hold_draft_tickets(add_to_date(now_datetime(), minutes=PAYMENT_HOLD_MINUTES))

	def booking_page(self) -> str:
		from buzz.api.booking.services import success_path  # services imports this module

		return f"/b{success_path(self.booking.name)}"

	def decline(self, message: str | None = None) -> None:
		self.validate_is_request()
		# Kept as a draft, so the organizer can reopen it.
		self.set_status("Rejected")
		self.send_email(
			"booking_request_declined",
			_("Update on your request to join {0}").format(self.event_title),
			message=(message or "").strip() or None,
		)

	def validate_is_request(self) -> None:
		if self.booking.docstatus != 0 or not self.booking.is_request:
			RequestNotOpen.throw()

	def send_received_email(self) -> None:
		self.send_email(
			"booking_request_received", _("We received your request to join {0}").format(self.event_title)
		)

	def send_email(self, builtin: str, subject: str, **args) -> None:
		try:
			self.booking.send_booking_email(
				template=None, builtin=builtin, subject=subject, always=True, **args
			)
		except Exception:
			frappe.log_error(
				title="Registration request email failed",
				reference_doctype=self.booking.doctype,
				reference_name=self.booking.name,
			)
