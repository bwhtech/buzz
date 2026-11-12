from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import get_fullname, get_url, getdate, today

from buzz.api.booking.exceptions import InviteExpired, InviteNotFound, InviteNotOpen, TooManyInvites
from buzz.api.booking.guests import get_or_create_guest_user
from buzz.api.booking.schemas import InviteDetails, InviteOutcome, InviteRequest, InviteSheetRow
from buzz.api.booking.services import get_booking_access_token, success_path, verify_booking_access_token
from buzz.api.events.services import manageable_event
from buzz.api.imports.sponsors import normalize
from buzz.api.imports.spreadsheet import Spreadsheet
from buzz.events.doctype.buzz_team_settings.buzz_team_settings import get_event_team_settings

if TYPE_CHECKING:
	from buzz.ticketing.doctype.event_booking.event_booking import EventBooking

INVITE_LIMIT = 50
MESSAGE_LIMIT = 300
# A guest holding one of these is asked already, so a second invite would only spam them.
SHEET_FIELDS = ("first_name", "last_name", "email", "tier")
# Header labels, normalized, that name each field.
SHEET_COLUMNS = {
	**{field: field for field in SHEET_FIELDS},
	"first": "first_name",
	"last": "last_name",
	"surname": "last_name",
	"e_mail": "email",
	"ticket": "tier",
	"ticket_type": "tier",
}
OPEN = ("Invited", "Requested", "Waitlisted", "Payment Pending")


class InviteService:
	"""Invites to one event, sent by anyone who can write its guest list."""

	def __init__(self, event: str):
		self.event = manageable_event(event, "guests")

	def send(self, invites: list[dict], message: str | None) -> list[InviteOutcome]:
		if len(message or "") > MESSAGE_LIMIT:
			frappe.throw(_("Keep the message under {0} characters").format(MESSAGE_LIMIT))
		return self.each_new_guest(self.validate_batch(invites), lambda row: self.invite(row, message))

	def preview(self, message: str | None) -> str:
		"""The invite email as a guest would get it, with a placeholder accept link."""
		return frappe.render_template(
			"buzz/templates/emails/booking_invite.html",
			{
				"event_doc": self.event,
				"event_title": self.event.title,
				"support_email": get_event_team_settings(self.event.name).support_email,
				"accept_url": "#",
				"message": (message or "").strip()[:MESSAGE_LIMIT] or None,
				"host": get_fullname(frappe.session.user),
			},
		)

	def add(self, invites: list[dict]) -> list[InviteOutcome]:
		rows = self.validate_batch(invites)
		if nameless := [row.email for row in rows if not row.first_name]:
			frappe.throw(_("Add a first name for {0}").format(", ".join(nameless)))
		return self.each_new_guest(rows, self.add_one)

	def each_new_guest(self, rows: list[InviteRequest], act) -> list[InviteOutcome]:
		"""Runs `act` once per new email; repeats are dropped, existing guests reported as skipped."""
		outcomes, seen = [], set()
		for row in rows:
			row.email = row.email.lower()
			if row.email in seen:
				continue
			seen.add(row.email)
			outcomes.append(self.skipped(row.email) or act(row))
		return outcomes

	def read_sheet(self, file_url: str | None, text: str | None) -> list[InviteSheetRow]:
		sheet = Spreadsheet.load(file_url, text)
		if len(sheet.rows) > INVITE_LIMIT:
			TooManyInvites.throw(limit=INVITE_LIMIT)
		columns = {SHEET_COLUMNS.get(normalize(label)): index for index, label in enumerate(sheet.header)}
		rows = [sheet_row(row, columns) for row in sheet.rows]
		return [row for row in rows if row.email]

	def validate_batch(self, invites: list[dict]) -> list[InviteRequest]:
		if len(invites) > INVITE_LIMIT:
			TooManyInvites.throw(limit=INVITE_LIMIT)
		return [InviteRequest.model_validate(row) for row in invites]

	def skipped(self, email: str) -> InviteOutcome | None:
		event = self.event.name
		if frappe.db.exists("Event Ticket", {"event": event, "attendee_email": email, "docstatus": 1}):
			return InviteOutcome(email=email, status="registered")
		if frappe.db.exists(
			"Event Booking", {"event": event, "user": email, "docstatus": 0, "status": ("in", OPEN)}
		):
			return InviteOutcome(email=email, status="already invited")
		return None

	def invite(self, row: InviteRequest, message: str | None) -> InviteOutcome:
		booking = self.create_booking(row)
		send_invite_email(booking, message)
		return InviteOutcome(email=row.email, status="invited", booking=booking.name)

	def add_one(self, row: InviteRequest) -> InviteOutcome:
		booking = self.create_booking(row)
		booking.submit()
		return InviteOutcome(email=row.email, status="added", booking=booking.name)

	def create_booking(self, row: InviteRequest) -> "EventBooking":
		"""A draft the guest submits by accepting; the organizer's pick overrides capacity and hidden tiers."""
		email = row.email
		first_name = row.first_name or email.split("@")[0]
		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.event.name,
				"user": invited_user(email, f"{first_name} {row.last_name or ''}"),
				"request_type": "Invite",
				"status": "Invited",
				"buyer_email": email,
				"attendees": [
					{
						"first_name": first_name,
						"last_name": row.last_name,
						"email": email,
						"ticket_type": row.ticket_type,
					}
				],
			}
		)
		booking.flags.organizer_override = True
		return booking.insert(ignore_permissions=True)


def sheet_row(cells: list[str], columns: dict) -> InviteSheetRow:
	return InviteSheetRow(
		**{field: cells[columns[field]] if field in columns else "" for field in SHEET_FIELDS}
	)


def invited_user(email: str, full_name: str) -> str:
	"""The organizer invites a capped, permissioned batch, so it skips the sign-up throttle."""
	importing = frappe.flags.in_import
	frappe.flags.in_import = True
	try:
		return get_or_create_guest_user(email, full_name)
	finally:
		frappe.flags.in_import = importing


def send_invite_email(booking: "EventBooking", message: str | None) -> None:
	accept_url = get_url(f"/b/invite/{booking.name}?token={get_booking_access_token(booking.name)}")
	event_title = frappe.get_cached_value("Buzz Event", booking.event, "title")
	booking.send_booking_email(
		template=None,
		builtin="booking_invite",
		subject=_("You're invited to {0}").format(event_title),
		always=True,
		accept_url=accept_url,
		message=(message or "").strip() or None,
		host=get_fullname(frappe.session.user),
	)


def invite_of(booking: str, token: str | None) -> "EventBooking":
	"""The invite a link points at; a wrong token reads the same as a missing invite."""
	if not verify_booking_access_token(booking, token):
		InviteNotFound.throw()
	doc = frappe.get_doc("Event Booking", booking)
	if not doc.is_invite:
		InviteNotFound.throw()
	return doc


def open_invite_of(booking: str, token: str | None) -> "EventBooking":
	doc = invite_of(booking, token)
	if doc.docstatus != 0 or doc.status != "Invited":
		InviteNotOpen.throw()
	if getdate(frappe.get_cached_value("Buzz Event", doc.event, "end_date")) < getdate(today()):
		InviteExpired.throw()
	# They registered on their own since; a second, free ticket would be a gift nobody chose.
	if frappe.db.exists(
		"Event Ticket", {"event": doc.event, "attendee_email": doc.attendees[0].email, "docstatus": 1}
	):
		InviteNotOpen.throw()
	return doc


def invite_details(doc: "EventBooking") -> InviteDetails:
	event = frappe.get_cached_doc("Buzz Event", doc.event)
	attendee = doc.attendees[0]
	return InviteDetails(
		event_title=event.title,
		start_date=event.start_date,
		start_time=event.start_time,
		venue=event.get_venue_name(),
		ticket_type=frappe.get_cached_value("Event Ticket Type", attendee.ticket_type, "title"),
		status=doc.status,
		first_name=None if is_placeholder_name(attendee) else attendee.first_name,
		last_name=attendee.last_name,
	)


def accept(doc: "EventBooking", first_name: str, last_name: str | None) -> str:
	"""The ticket carries the name the guest gives; submitting issues it free."""
	attendee = doc.attendees[0]
	attendee.first_name = first_name.strip()
	attendee.last_name = (last_name or "").strip()
	doc.flags.ignore_permissions = True
	doc.flags.organizer_override = True
	doc.submit()
	return success_path(doc.name)


def is_placeholder_name(attendee) -> bool:
	"""An invite by email alone names the guest after the email prefix until they give a name."""
	return attendee.first_name == attendee.email.split("@")[0] and not attendee.last_name


def decline(doc: "EventBooking") -> None:
	"""Kept as a draft, like a declined request, so the organizer sees the answer."""
	doc.status = "Rejected"
	doc.flags.ignore_permissions = True
	doc.flags.organizer_override = True
	doc.save()


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=20, seconds=3600)
def send_invites(event: str, invites: list[dict], message: str | None = None) -> list[InviteOutcome]:
	return InviteService(event).send(invites, message)


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True)
@rate_limit(limit=30, seconds=600)
def get_invite(booking: str, token: str) -> InviteDetails:
	return invite_details(invite_of(booking, token))


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=600)
def accept_invite(booking: str, token: str, first_name: str, last_name: str | None = None) -> str:
	return accept(open_invite_of(booking, token), first_name, last_name)


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=600)
def decline_invite(booking: str, token: str) -> None:
	decline(open_invite_of(booking, token))


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=20, seconds=3600)
def add_guests(event: str, invites: list[dict]) -> list[InviteOutcome]:
	return InviteService(event).add(invites)


@frappe.whitelist()
def preview_invite(event: str, message: str | None = None) -> str:
	return InviteService(event).preview(message)


@frappe.whitelist(methods=["POST"])
def read_invite_sheet(
	event: str, file_url: str | None = None, text: str | None = None
) -> list[InviteSheetRow]:
	return InviteService(event).read_sheet(file_url, text)
