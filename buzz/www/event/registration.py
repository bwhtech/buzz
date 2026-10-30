from functools import cached_property

import frappe
from frappe import _
from frappe.utils import fmt_money, format_date

from buzz.api.booking.event_data import get_available_ticket_types
from buzz.api.booking.services import are_registrations_closed
from buzz.api.events.services import registration_link
from buzz.api.proposals.services import are_proposals_closed, proposal_form, proposal_link
from buzz.ticketing.doctype.ticket_hold.ticket_hold import held_quantities


class RegistrationCard:
	"""The side panel's registration card: one state, its copy and its action."""

	def __init__(self, event):
		self.event = event

	def as_dict(self) -> dict:
		return self.state_card() | {"booked": self.booked_tickets()}

	def state_card(self) -> dict:
		if are_registrations_closed(self.event):
			return self.card(
				"closed", _("Registrations closed"), _("This event is not taking registrations.")
			)
		if self.event.external_registration_page:
			return self.open_card("")
		if not self.ticket_types:
			return self.unavailable_card()
		return self.open_card(self.ticket_summary())

	def unavailable_card(self) -> dict:
		published = self.published_ticket_types()
		if not published:
			return self.open_card("")
		if any(held_quantities(published).values()):
			return self.card(
				"reserved",
				_("All tickets are reserved"),
				_("People are checking out. Tickets come back if they don't finish."),
			)
		return self.card("sold-out", _("Sold out"), _("All tickets have been taken."))

	def booked_tickets(self) -> dict | None:
		count = self.booked_ticket_count
		if not count:
			return None
		label = _("1 ticket") if count == 1 else _("{0} tickets").format(count)
		return {"label": label, "url": "/b/account/bookings"}

	def published_ticket_types(self) -> list:
		filters = {"event": self.event.name, "is_published": 1, "is_hidden": 0}
		return frappe.get_all("Event Ticket Type", filters=filters, pluck="name")

	def open_card(self, subtitle: str) -> dict:
		register_url = registration_link(self.event)
		label = _("Book more tickets") if self.booked_ticket_count else _("Register")
		return self.card("open", _("Registration open"), subtitle, label, register_url, primary=True)

	def card(self, state, title, subtitle, action_label=None, action_url=None, primary=False) -> dict:
		return {
			"state": state,
			"title": title,
			"subtitle": subtitle,
			"action_label": action_label,
			"action_url": action_url,
			"primary": primary,
		}

	@cached_property
	def booked_ticket_count(self) -> int:
		if frappe.session.user == "Guest":
			return 0
		bookings = frappe.get_all(
			"Event Booking",
			filters={"event": self.event.name, "user": frappe.session.user, "docstatus": 1},
			pluck="name",
		)
		filters = {"booking": ["in", bookings], "docstatus": 1}
		return frappe.db.count("Event Ticket", filters) if bookings else 0

	@cached_property
	def ticket_types(self) -> list:
		return get_available_ticket_types(self.event.name)

	def ticket_summary(self) -> str:
		return " · ".join(part for part in [self.price_label(), self.spots_label()] if part)

	def price_label(self) -> str:
		ticket_types = self.ticket_types
		paid = [ticket_type.prices[0] for ticket_type in ticket_types if not ticket_type.is_free]
		if not paid:
			return _("Free")
		lowest = min(paid, key=lambda row: row.price)
		price = fmt_money(lowest.price, currency=lowest.currency, precision=0)
		if len(paid) < len(ticket_types):
			return _("Free, or from {0}").format(price)
		return _("From {0}").format(price) if len(paid) > 1 else price

	def spots_label(self) -> str | None:
		remaining = [ticket_type.remaining_tickets for ticket_type in self.ticket_types]
		if -1 in remaining:
			return None
		return _("{0} spots left").format(sum(remaining))


class ProposalCard:
	"""The call for proposals card, shown while the event's talk proposal form takes submissions."""

	def __init__(self, event):
		self.event = event

	def as_dict(self) -> dict | None:
		url = proposal_link(self.event)
		if not url or are_proposals_closed(self.event):
			return None
		return {
			"title": _("Call for proposals open"),
			"subtitle": self.closing_note(),
			"action_label": _("Submit a talk"),
			"action_url": url,
		}

	def closing_note(self) -> str:
		closes_at = proposal_form(self.event).auto_close_at
		if not closes_at:
			return _("Submit a talk for this event.")
		return _("Submissions close {0}.").format(format_date(closes_at, "d MMM"))
