from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.utils import cint, now_datetime, time_diff_in_seconds

from buzz.api.booking.exceptions import RegistrationsClosed, TicketsUnavailable, TooManyTicketsHeld
from buzz.api.booking.schemas import TicketHoldResponse
from buzz.api.booking.services import are_registrations_closed
from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import (
	lock_ticket_types,
	start_capacity_transaction,
)
from buzz.ticketing.doctype.ticket_hold.ticket_hold import (
	held_from_ip,
	live_hold_expiry,
	new_hold_expiry,
	release_hold,
	set_hold,
)

if TYPE_CHECKING:
	from buzz.events.doctype.buzz_event.buzz_event import BuzzEvent
	from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import EventTicketType


# One network can hold this many tickets at a time, so a script can't hold a whole event.
MAX_TICKETS_PER_IP = 20


class TicketHoldService:
	"""Set the tickets one booking form holds. A resize keeps the hold's expiry, so a client
	can't extend it; a token whose hold has lapsed is replaced by a new one."""

	def __init__(self, event: str, quantities: dict, hold_token: str | None):
		self.event_name = str(event)
		self.quantities = {
			str(name): cint(quantity) for name, quantity in quantities.items() if cint(quantity) > 0
		}
		self.hold_token = hold_token

	@property
	def event(self) -> "BuzzEvent":
		return frappe.get_cached_doc("Buzz Event", self.event_name)

	def hold(self) -> TicketHoldResponse:
		start_capacity_transaction()
		self.validate_event()
		self.validate_ip_limit()
		ticket_types = self.limited_ticket_types()
		lock_ticket_types([row.name for row in ticket_types])
		expires_at = self.resolve_expiry()
		remaining = {str(row.name): self.check_capacity(row) for row in ticket_types}
		held = {name: self.quantities[name] for name in remaining}
		set_hold(self.hold_token, self.event_name, held, expires_at)
		return TicketHoldResponse(
			hold_token=self.hold_token,
			expires_in_seconds=self.seconds_until(expires_at) if any(held.values()) else None,
			remaining=remaining,
		)

	def validate_event(self) -> None:
		if not self.event.is_published:
			frappe.throw(_("Event is not live"))
		if are_registrations_closed(self.event):
			RegistrationsClosed.throw()
		if frappe.session.user == "Guest" and not self.event.allow_guest_booking:
			frappe.throw(_("Please log in to access this feature"), frappe.AuthenticationError)

	# Checked before any ticket type is read, so a huge request costs one query.
	def validate_ip_limit(self) -> None:
		ip_address = getattr(frappe.local, "request_ip", None)
		if not ip_address:
			return
		held = held_from_ip(ip_address, self.hold_token)
		if held + sum(self.quantities.values()) > MAX_TICKETS_PER_IP:
			TooManyTicketsHeld.throw(limit=MAX_TICKETS_PER_IP)

	def limited_ticket_types(self) -> list["EventTicketType"]:
		ticket_types = [frappe.get_cached_doc("Event Ticket Type", name) for name in self.quantities]
		for ticket_type in ticket_types:
			if str(ticket_type.event) != self.event_name or not ticket_type.is_published:
				frappe.throw(_("{0} is not available for this event").format(ticket_type.title))
		return [ticket_type for ticket_type in ticket_types if ticket_type.max_tickets_available]

	def resolve_expiry(self):
		expires_at = live_hold_expiry(self.hold_token)
		if expires_at:
			return expires_at
		release_hold(self.hold_token)
		self.hold_token = frappe.generate_hash(length=32)
		return new_hold_expiry()

	def check_capacity(self, ticket_type: "EventTicketType") -> int:
		remaining = ticket_type.get_remaining_tickets(for_update=True, hold_token=self.hold_token)
		if remaining < self.quantities[str(ticket_type.name)]:
			TicketsUnavailable.throw(remaining=max(remaining, 0), ticket_type=ticket_type.title)
		return remaining

	@staticmethod
	def seconds_until(expires_at) -> int:
		return max(cint(time_diff_in_seconds(expires_at, now_datetime())), 0)
