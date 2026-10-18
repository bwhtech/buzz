from datetime import datetime

import frappe
from frappe.utils import validate_email_address

from buzz.api.communications.exceptions import CannotSendCommunication, NoRecipients, UnknownAudience
from buzz.api.communications.schemas import (
	CommunicationItem,
	EventCommunicationsResponse,
	RecipientCount,
)
from buzz.api.events.services import ensure_event_team_access, guest_filter_fields
from buzz.api.filters.conditions import ListConditions
from buzz.api.filters.schemas import FilterField
from buzz.api.proposals.services import proposal_filter_fields
from buzz.api.sponsorships.sponsors import sponsor_filter_fields
from buzz.api.teams.exceptions import CannotEditTeam
from buzz.permissions import can_manage_members, has_team_access


def guest_emails(event: str, filters: str | None) -> list[str]:
	"""Every submitted ticket holder. A draft belongs to a booking still being paid for."""
	fields, answer_parents = guest_filter_fields(event)
	conditions = ListConditions("Event Ticket", fields, answer_parents).frappe_filters(filters)
	query_filters = [["event", "=", event], ["docstatus", "=", 1], *conditions]
	return frappe.get_all("Event Ticket", filters=query_filters, pluck="attendee_email", distinct=True)


def speaker_emails(event: str, filters: str | None) -> list[str]:
	"""Every speaker listed on the event's proposals that match the filters."""
	conditions = ListConditions("Talk Proposal", proposal_filter_fields(event)).frappe_filters(filters)
	proposals = frappe.get_all("Talk Proposal", filters=[["event", "=", event], *conditions], pluck="name")
	if not proposals:
		return []
	return frappe.get_all(
		"Proposal Speaker",
		filters={"parenttype": "Talk Proposal", "parent": ["in", proposals]},
		pluck="email",
		distinct=True,
	)


def sponsor_emails(event: str, filters: str | None) -> list[str]:
	"""The contact email of every sponsor that matches the filters."""
	conditions = ListConditions("Event Sponsor", sponsor_filter_fields(event)).frappe_filters(filters)
	return frappe.get_all(
		"Event Sponsor", filters=[["event", "=", event], *conditions], pluck="contact_email", distinct=True
	)


RECIPIENT_SOURCES = {"Guests": guest_emails, "Speakers": speaker_emails, "Sponsors": sponsor_emails}


def recipients_of(event: str, audience: str, filters: str | None) -> list[str]:
	"""Each address once, whichever audience it comes from."""
	if audience not in RECIPIENT_SOURCES:
		UnknownAudience.throw(audience=audience)
	return sorted({email for email in RECIPIENT_SOURCES[audience](event, filters) if email})


def filter_fields_by_audience(event: str) -> dict[str, list[FilterField]]:
	"""The same filters each audience's own list page offers."""
	return {
		"Guests": guest_filter_fields(event)[0],
		"Speakers": proposal_filter_fields(event),
		"Sponsors": sponsor_filter_fields(event),
	}


def count_recipients(event: str, audience: str, filters: str | None):
	ensure_event_team_access(event)
	return RecipientCount(count=len(recipients_of(event, audience, filters)))


def team_of(event: str) -> str:
	return frappe.get_cached_value("Buzz Event", event, "team")


def send_communication(
	event: str,
	audience: str,
	message: str,
	subject: str,
	filters: str,
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
			"filters": filters,
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
		filters=row.filters or "",
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
			"filters",
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
		filter_fields=filter_fields_by_audience(event),
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
