from datetime import datetime

import frappe
from frappe.utils import validate_email_address

from buzz.api.communications.exceptions import CannotSendCommunication, NoRecipients, UnknownAudience
from buzz.api.communications.schemas import (
	CommunicationItem,
	EventCommunicationsResponse,
	RecipientCount,
)
from buzz.api.events.services import ensure_event_team_access, ticket_type_filter, ticket_types_of
from buzz.api.teams.exceptions import CannotEditTeam
from buzz.permissions import can_manage_members, has_team_access

AUDIENCES = ("Guests", "Speakers")


def split_csv(value: str | None) -> list[str]:
	return [item.strip() for item in (value or "").split(",") if item.strip()]


def guest_emails(event: str, ticket_types: str | None = None) -> list[str]:
	"""Every submitted ticket holder, once. A draft belongs to a booking still being paid for."""
	filters: dict = {"event": event, "docstatus": 1}
	chosen = ticket_type_filter(ticket_types)
	if chosen:
		filters["ticket_type"] = ["in", chosen]
	rows = frappe.get_all("Event Ticket", filters=filters, pluck="attendee_email", distinct=True)
	return sorted({email for email in rows if email})


def speaker_emails(event: str, statuses: str | None = None) -> list[str]:
	"""Every speaker listed on the event's proposals, once. Statuses narrow the proposals first."""
	filters: dict = {"event": event}
	chosen = split_csv(statuses)
	if chosen:
		filters["status"] = ["in", chosen]
	proposals = frappe.get_all("Talk Proposal", filters=filters, pluck="name")
	if not proposals:
		return []
	rows = frappe.get_all(
		"Proposal Speaker",
		filters={"parenttype": "Talk Proposal", "parent": ["in", proposals]},
		pluck="email",
		distinct=True,
	)
	return sorted({email for email in rows if email})


def recipients_of(event: str, audience: str, ticket_types: str | None, statuses: str | None) -> list[str]:
	if audience == "Guests":
		return guest_emails(event, ticket_types)
	if audience == "Speakers":
		return speaker_emails(event, statuses)
	UnknownAudience.throw(audience=audience)


def count_recipients(event: str, audience: str, ticket_types: str | None, statuses: str | None):
	ensure_event_team_access(event)
	return RecipientCount(count=len(recipients_of(event, audience, ticket_types, statuses)))


def team_of(event: str) -> str:
	return frappe.get_cached_value("Buzz Event", event, "team")


def send_communication(
	event: str,
	audience: str,
	message: str,
	subject: str,
	ticket_types: str,
	statuses: str,
	scheduled_at: datetime | None,
) -> CommunicationItem:
	"""Insert the record; its controller resolves the recipients and hands them to sendmail."""
	ensure_event_team_access(event)
	if not has_team_access(team_of(event), "write", frappe.session.user):
		CannotSendCommunication.throw()

	doc = frappe.get_doc(
		{
			"doctype": "Event Communication",
			"event": event,
			"audience": audience,
			"ticket_types": ticket_types,
			"statuses": statuses,
			"subject": subject,
			"message": message,
			"scheduled_at": scheduled_at,
		}
	).insert(ignore_permissions=True)
	return item_of(doc.as_dict(), sent_by=frappe.utils.get_fullname(doc.owner))


def item_of(row, sent_by: str) -> CommunicationItem:
	return CommunicationItem(
		name=row.name,
		audience=row.audience,
		ticket_types=row.ticket_types or "",
		statuses=row.statuses or "",
		subject=row.subject or "",
		message=row.message or "",
		recipient_count=row.recipient_count or 0,
		scheduled_at=row.scheduled_at,
		sent_by=sent_by,
		creation=row.creation,
	)


def event_communications(event: str) -> EventCommunicationsResponse:
	ensure_event_team_access(event)
	team = team_of(event)
	rows = frappe.get_all(
		"Event Communication",
		filters={"event": event},
		fields=[
			"name",
			"audience",
			"ticket_types",
			"statuses",
			"subject",
			"message",
			"recipient_count",
			"scheduled_at",
			"owner",
			"creation",
		],
		order_by="creation desc, name desc",
	)
	names = frappe.get_all(
		"User", filters={"name": ["in", {row.owner for row in rows}]}, fields=["name", "full_name"]
	)
	full_names = {user.name: user.full_name for user in names}
	settings = frappe.get_cached_doc("Buzz Team Settings", team)
	return EventCommunicationsResponse(
		title=frappe.get_cached_value("Buzz Event", event, "title"),
		can_write=has_team_access(team, "write", frappe.session.user),
		can_edit_settings=can_manage_members(team),
		support_email=settings.support_email or None,
		ticket_types=ticket_types_of(event),
		statuses=frappe.get_all("Talk Proposal Status", pluck="name", order_by="creation asc"),
		communications=[item_of(row, full_names.get(row.owner) or row.owner) for row in rows],
	)


def update_support_email(event: str, support_email: str) -> None:
	ensure_event_team_access(event)
	team = team_of(event)
	if not can_manage_members(team):
		CannotEditTeam.throw()
	support_email = support_email.strip()
	if support_email:
		validate_email_address(support_email, throw=True)
	frappe.db.set_value("Buzz Team Settings", team, "support_email", support_email or None)
	frappe.clear_document_cache("Buzz Team Settings", team)
