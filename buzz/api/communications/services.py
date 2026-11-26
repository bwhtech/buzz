from datetime import datetime

import frappe
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Count
from frappe.utils import validate_email_address

from buzz.api.communications.exceptions import CannotSendCommunication, UnknownAudience
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
from buzz.permissions import can_manage_members, has_section_permission


def _recipient_query(event: str, audience: str, filters: str | None, *, count_only: bool = False):
	event_id = str(event)
	if audience == "Guests":
		fields, answer_parents = guest_filter_fields(event_id)
		ticket = frappe.qb.DocType("Event Ticket")
		standard_filters, extra_criteria = ListConditions(
			"Event Ticket", fields, answer_parents, event=event_id
		).split_qb_criteria(filters, ticket)
		select_fields = [Count(ticket.attendee_email).distinct()] if count_only else ["attendee_email"]
		query = frappe.qb.get_query(
			"Event Ticket",
			fields=select_fields,
			filters=[
				["event", "=", event_id],
				["docstatus", "=", 1],
				["attendee_email", "is", "set"],
				*standard_filters,
			],
			distinct=not count_only,
			order_by=None if count_only else "attendee_email asc",
			ignore_permissions=True,
		)
		if extra_criteria:
			query = query.where(Criterion.all(extra_criteria))
		return query

	if audience == "Speakers":
		proposal = frappe.qb.DocType("Talk Proposal")
		speaker = frappe.qb.DocType("Proposal Speaker")
		standard_filters, extra_criteria = ListConditions(
			"Talk Proposal", proposal_filter_fields(event_id), event=event_id
		).split_qb_criteria(filters, proposal)
		query = (
			frappe.qb.get_query(
				"Talk Proposal",
				fields=[Count(speaker.email).distinct()] if count_only else [speaker.email],
				filters=[["event", "=", event_id], *standard_filters],
				distinct=not count_only,
				ignore_permissions=True,
			)
			.join(speaker)
			.on(speaker.parent == proposal.name)
			.where(
				Criterion.all(
					[
						speaker.parenttype == "Talk Proposal",
						speaker.email.isnotnull(),
						speaker.email != "",
						*extra_criteria,
					]
				)
			)
		)
		if not count_only:
			query = query.orderby(speaker.email)
		return query

	if audience == "Sponsors":
		sponsor = frappe.qb.DocType("Event Sponsor")
		standard_filters, extra_criteria = ListConditions(
			"Event Sponsor", sponsor_filter_fields(event_id)
		).split_qb_criteria(filters, sponsor)
		select_fields = [Count(sponsor.contact_email).distinct()] if count_only else ["contact_email"]
		query = frappe.qb.get_query(
			"Event Sponsor",
			fields=select_fields,
			filters=[["event", "=", event_id], ["contact_email", "is", "set"], *standard_filters],
			distinct=not count_only,
			order_by=None if count_only else "contact_email asc",
			ignore_permissions=True,
		)
		if extra_criteria:
			query = query.where(Criterion.all(extra_criteria))
		return query

	UnknownAudience.throw(audience=audience)


def recipients_of(event: str, audience: str, filters: str | None) -> list[str]:
	"""Each address once, whichever audience it comes from."""
	return _recipient_query(event, audience, filters).run(pluck=True)


def filter_fields_by_audience(event: str, team: str | None = None) -> dict[str, list[FilterField]]:
	"""The same filters each audience's own list page offers."""
	return {
		"Guests": guest_filter_fields(event)[0],
		"Speakers": proposal_filter_fields(event),
		"Sponsors": sponsor_filter_fields(event, team=team),
	}


def count_recipients(event: str, audience: str, filters: str | None):
	ensure_event_team_access(event, "communications")
	rows = _recipient_query(event, audience, filters, count_only=True).run()
	return RecipientCount(count=rows[0][0] if rows else 0)


def team_of(event: str) -> str:
	return frappe.get_cached_value("Buzz Event", str(event), "team")


def send_communication(
	event: str,
	audience: str,
	message: str,
	subject: str,
	filters: str,
	scheduled_at: datetime | None,
) -> CommunicationItem:
	"""Insert the record; its controller resolves the recipients and hands them to sendmail."""
	event_doc = ensure_event_team_access(event, "communications")
	if not has_section_permission(
		event, "communications", "write", frappe.session.user, team=event_doc.team or ""
	):
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
	doc = ensure_event_team_access(event, "communications")
	event_id = str(doc.name)
	team = doc.team or ""
	rows = frappe.get_all(
		"Event Communication",
		filters={"event": event_id},
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
		ignore_permissions=True,
	)
	owners = {row.owner for row in rows if row.owner}
	names = (
		frappe.get_all("User", filters={"name": ["in", list(owners)]}, fields=["name", "full_name"])
		if owners
		else []
	)
	full_names = {user.name: user.full_name for user in names}
	settings = frappe.get_cached_doc("Buzz Team Settings", team)
	return EventCommunicationsResponse(
		title=doc.title,
		can_write=has_section_permission(event_id, "communications", "write", frappe.session.user, team=team),
		can_edit_settings=can_manage_members(team),
		support_email=settings.support_email or None,
		filter_fields=filter_fields_by_audience(event_id, team=team),
		communications=[item_of(row, full_names.get(row.owner) or row.owner) for row in rows],
	)


def update_support_email(event: str, support_email: str) -> None:
	doc = ensure_event_team_access(event, "communications")
	team = doc.team or ""
	if not can_manage_members(team):
		CannotEditTeam.throw()
	support_email = support_email.strip()
	if support_email:
		validate_email_address(support_email, throw=True)
	frappe.db.set_value("Buzz Team Settings", team, "support_email", support_email or None)
	frappe.clear_document_cache("Buzz Team Settings", team)
