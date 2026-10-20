from functools import cached_property
from typing import ClassVar

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, format_date, getdate

from buzz.api.checkin.services import CheckinService
from buzz.api.exceptions import NotPermitted
from buzz.api.imports.schemas import ImportCheck, ImportOption
from buzz.api.imports.services import Field, Importer
from buzz.permissions import can_check_in

SUBMITTED = 1


class CheckInImporter(Importer):
	"""One row checks in a ticket, or every ticket an email holds, on a day of the event."""

	section = "guests"
	noun = "check-ins"
	fields: ClassVar[dict[str, Field]] = {
		"ticket": Field(
			"Ticket ID", aliases=("ticket_id", "ticket", "ticket_no", "ticket_number", "ticket_code")
		),
		"email": Field("Email", aliases=("attendee_email", "e_mail", "email_address", "guest_email")),
		"date": Field("Date", aliases=("check_in_date", "checkin_date", "day")),
	}

	def ensure_permitted(self) -> None:
		if not can_check_in(self.event, frappe.session.user):
			NotPermitted.throw()

	def missing_fields(self) -> list[str]:
		return [] if {"ticket", "email"} & set(self.mapping) else [_("Ticket ID or Email")]

	@cached_property
	def tickets(self) -> list[dict]:
		return frappe.get_all(
			"Event Ticket", filters={"event": self.event}, fields=["name", "attendee_email", "docstatus"]
		)

	@cached_property
	def tickets_by_name(self) -> dict[str, dict]:
		return {ticket.name: ticket for ticket in self.tickets}

	@cached_property
	def tickets_by_email(self) -> dict[str, list[str]]:
		by_email: dict[str, list[str]] = {}
		for ticket in self.tickets:
			if ticket.docstatus == SUBMITTED and ticket.attendee_email:
				by_email.setdefault(ticket.attendee_email.lower(), []).append(ticket.name)
		return by_email

	@property
	def days(self) -> list:
		start = getdate(self.event_doc.start_date)
		end = getdate(self.event_doc.end_date or start)
		return [add_days(start, offset) for offset in range(date_diff(end, start) + 1)]

	def row_error(self, record: dict) -> str | None:
		return self.resolve_date(record) or self.resolve_tickets(record)

	def resolve_date(self, record: dict) -> str | None:
		raw = record.get("date")
		try:
			record["date"] = getdate(raw or self.choices.get("date") or self.days[0])
		except Exception:
			return _("{0} isn't a date.").format(raw)
		if record["date"] not in self.days:
			return _("{0} isn't a day of this event.").format(format_date(record["date"]))
		return None

	def resolve_tickets(self, record: dict) -> str | None:
		if ticket_id := record.get("ticket"):
			ticket = self.tickets_by_name.get(ticket_id)
			if not ticket:
				return _("Ticket {0} isn't for this event.").format(ticket_id)
			if ticket.docstatus != SUBMITTED:
				return _("Ticket {0} is cancelled.").format(ticket_id)
			record["tickets"] = [ticket_id]
			return None
		email = record.get("email")
		if not email:
			return _("Ticket ID and email are both empty.")
		record["tickets"] = self.tickets_by_email.get(email.lower())
		return None if record["tickets"] else _("No ticket is held by {0}.").format(email)

	def duplicate_keys(self, record: dict) -> list[str]:
		return [f"{ticket}|{record['date']}" for ticket in record["tickets"]]

	@cached_property
	def checked_in(self) -> set[str]:
		checkins = frappe.get_all(
			"Event Check In", filters={"event": self.event, "docstatus": SUBMITTED}, fields=["ticket", "date"]
		)
		return {f"{row.ticket}|{getdate(row.date)}" for row in checkins}

	def existing_keys(self) -> set[str]:
		return set(self.checked_in)

	def import_record(self, record: dict) -> None:
		for ticket in record["tickets"]:
			if f"{ticket}|{record['date']}" in self.checked_in:
				continue
			checkin = CheckinService(ticket)
			checkin.date = record["date"]
			checkin.ensure_checkin_allowed()
			checkin.record_checkin()

	def check(self) -> ImportCheck:
		check = super().check()
		if "date" not in self.mapping:
			check.days = [ImportOption(value=str(day), label=format_date(day)) for day in self.days]
		return check
