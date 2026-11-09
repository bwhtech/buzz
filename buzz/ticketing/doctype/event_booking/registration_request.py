from typing import TYPE_CHECKING

import frappe
from frappe import _

from buzz.api.booking.exceptions import RequestAlreadyOpen, RequestNotOpen
from buzz.permissions import has_section_permission

if TYPE_CHECKING:
	from buzz.ticketing.doctype.event_booking.event_booking import EventBooking

REQUEST_STATUSES = ("Requested",)
OPEN_STATUSES = REQUEST_STATUSES


class RegistrationRequest:
	"""A draft booking an organizer approves or declines before it is confirmed."""

	def __init__(self, booking: "EventBooking"):
		self.booking = booking

	@property
	def event_title(self) -> str:
		return frappe.get_cached_value("Buzz Event", self.booking.event, "title")

	def initial_status(self) -> str | None:
		"""The request status a new booking starts in, or None when it books straight away."""
		if has_section_permission(self.booking.event, "guests", "create", frappe.session.user):
			return None
		if any(ticket_type.needs_approval for ticket_type in self.ticket_types()):
			return "Requested"
		return None

	def ticket_types(self) -> list:
		return [frappe.get_cached_doc("Event Ticket Type", name) for name in self.booking.ticket_quantities()]

	def validate_no_open_request(self) -> None:
		filters = {"event": self.booking.event, "user": self.booking.user, "docstatus": 0}
		if frappe.db.exists("Event Booking", {**filters, "status": ("in", OPEN_STATUSES)}):
			RequestAlreadyOpen.throw()

	def approve(self) -> None:
		self.validate_is_request()
		self.booking.flags.ignore_permissions = True
		self.booking.status = "Confirmed"
		# validate checks capacity again; on_submit issues the tickets and emails them.
		self.booking.submit()

	def decline(self, message: str | None = None) -> None:
		self.validate_is_request()
		self.booking.flags.ignore_permissions = True
		self.booking.discard()
		self.booking.db_set("status", "Rejected")
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
