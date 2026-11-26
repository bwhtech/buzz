import frappe
from frappe import _
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Count, Date
from frappe.utils import add_days, getdate
from pypika.terms import ExistsCriterion, ValueWrapper

from buzz.api.events.exceptions import CannotManageEvent
from buzz.api.events.services import ensure_event_team_access
from buzz.api.filters.conditions import ListConditions, filter_field, form_questions, question_fields
from buzz.api.filters.schemas import FilterField
from buzz.api.proposals.exceptions import ProposalFormMissing
from buzz.api.proposals.schemas import (
	AcceptedProposal,
	DailySubmissions,
	EventProposalsResponse,
	ProposalListItem,
	ProposalSpeakerItem,
	ProposalState,
	ProposalTrend,
	StatusTotal,
)
from buzz.events.doctype.buzz_form.form_types import TALK_PROPOSAL_FORM_DOCTYPE as PROPOSAL_FORM_DOCTYPE
from buzz.events.doctype.buzz_form.form_types import event_form, is_form_closed
from buzz.events.doctype.event_venue.event_venue import set_venue_names
from buzz.permissions import derived_has_permission, has_section_permission

# The columns behind one proposal card. The event ones come over a link hop, so a
# deleted event leaves them empty.
PROPOSAL_LIST_FIELDS = [
	"name",
	"title",
	"event",
	"event.title as event_title",
	"event.start_date",
	"event.start_time",
	"event.end_date",
	"event.venue as venue",
	"event.banner_image",
	"event.allow_editing_talks_after_acceptance",
	"status",
	"creation",
	"modified",
]


def my_proposals() -> list[ProposalListItem]:
	"""Proposals where the session user is the submitter or a listed speaker.

	Speaker matching runs on the speakers child table because guest form
	submissions leave submitted_by as "Guest".
	"""
	user = frappe.session.user

	speaker_proposal_names = frappe.get_all(
		"Proposal Speaker",
		filters={"parenttype": "Talk Proposal", "email": user},
		pluck="parent",
	)

	rows = frappe.get_all(
		"Talk Proposal",
		or_filters={
			"submitted_by": user,
			"name": ["in", speaker_proposal_names],
		},
		fields=PROPOSAL_LIST_FIELDS,
		order_by="creation desc",
		ignore_permissions=True,
	)

	speakers = speakers_by_proposal([row.name for row in rows])
	set_venue_names(rows)

	return [ProposalListItem(**row, speakers=speakers.get(row.name, [])) for row in rows]


def speakers_by_proposal(proposal_names: list[str]) -> dict[str, list[ProposalSpeakerItem]]:
	"""Speaker rows for many proposals in one query, keyed by proposal."""
	if not proposal_names:
		return {}

	rows = frappe.get_all(
		"Proposal Speaker",
		filters={"parenttype": "Talk Proposal", "parent": ["in", proposal_names]},
		fields=["parent", "first_name", "last_name", "email"],
		order_by="parent asc, idx asc",
	)

	grouped: dict[str, list[ProposalSpeakerItem]] = {}
	for row in rows:
		grouped.setdefault(row.pop("parent"), []).append(ProposalSpeakerItem(**row))
	return grouped


PROPOSALS_PAGE_SIZE = 20
TREND_DAYS = 14


def event_proposals(
	event: str,
	search: str | None = None,
	filters: str | None = None,
	order: str = "desc",
	start: int = 0,
	limit: int = PROPOSALS_PAGE_SIZE,
	name: str | None = None,
) -> EventProposalsResponse:
	"""One page of the talk proposals submitted to an event, newest first by default.

	Read access to the event's team is the bar, the same one its guest list uses.
	"""
	doc = ensure_event_team_access(event, "talks")
	event_id = str(doc.name)

	filter_fields = proposal_filter_fields(event_id)
	proposal = frappe.qb.DocType("Talk Proposal")
	standard_filters, extra_criteria = ListConditions(
		"Talk Proposal", filter_fields, event=event_id
	).split_qb_criteria(filters, proposal)
	if name:
		standard_filters.append(["name", "=", name])
	if term := (search or "").strip():
		pattern = f"%{term}%"
		speaker = frappe.qb.DocType("Proposal Speaker")
		speaker_match = ExistsCriterion(
			frappe.qb.from_(speaker)
			.select(ValueWrapper(1))
			.where(
				(speaker.parenttype == "Talk Proposal")
				& (speaker.parent == proposal.name)
				& (
					speaker.first_name.like(pattern)
					| speaker.last_name.like(pattern)
					| speaker.email.like(pattern)
				)
			)
		)
		extra_criteria.append(proposal.title.like(pattern) | speaker_match)
	limit = max(1, min(int(limit), 100))
	start = max(0, int(start))
	direction = "asc" if str(order).lower() == "asc" else "desc"

	base_filters = [["event", "=", event_id], *standard_filters]
	query = frappe.qb.get_query(
		"Talk Proposal",
		fields=["name", "title", "event", "status", "creation", "modified"],
		filters=base_filters,
		order_by=f"creation {direction}, name {direction}",
		limit=limit,
		offset=start,
		ignore_permissions=True,
	)
	if extra_criteria:
		query = query.where(Criterion.all(extra_criteria))
	rows = query.run(as_dict=True)
	speakers = speakers_by_proposal([row.name for row in rows])
	event_meta = {
		"event_title": doc.title,
		"start_date": doc.start_date,
		"start_time": doc.start_time,
		"end_date": doc.end_date,
		"venue": doc.venue,
		"banner_image": doc.banner_image,
		"allow_editing_talks_after_acceptance": doc.allow_editing_talks_after_acceptance,
	}

	is_filtered = bool(standard_filters or extra_criteria)
	total = (
		len(rows)
		if not is_filtered and start == 0 and len(rows) < limit
		else frappe.db.count("Talk Proposal", {"event": event_id})
	)
	if not is_filtered:
		matched = total
	elif start == 0 and len(rows) < limit:
		matched = len(rows)
	else:
		count_query = frappe.qb.get_query(
			"Talk Proposal",
			fields=[Count(proposal.name)],
			filters=base_filters,
			ignore_permissions=True,
		)
		if extra_criteria:
			count_query = count_query.where(Criterion.all(extra_criteria))
		count_rows = count_query.run()
		matched = count_rows[0][0] if count_rows else 0

	form_row = frappe.db.get_value(
		"Buzz Form",
		{"event": event_id, "form_doctype": PROPOSAL_FORM_DOCTYPE},
		["name", "route", "publish", "auto_close_at"],
		as_dict=True,
	)
	return EventProposalsResponse(
		title=doc.title,
		total=total,
		matched=matched,
		proposals=[
			ProposalListItem(**row, **event_meta, speakers=speakers.get(row.name, [])) for row in rows
		],
		has_next_page=start + len(rows) < matched,
		can_write=has_section_permission(
			event_id, "talks", "write", frappe.session.user, team=doc.team or ""
		),
		proposal_link=f"/b/{doc.route}/{form_row.route}" if form_row and doc.route else None,
		proposal_form=form_row.name if form_row else None,
		proposals_closed=(
			is_form_closed(form_row.publish, form_row.auto_close_at, doc.time_zone) if form_row else True
		),
		filter_fields=filter_fields,
	)


def proposal_filter_fields(event: str) -> list[FilterField]:
	"""Status, then the questions on the event's talk proposal form."""
	statuses = frappe.get_all("Talk Proposal Status", pluck="name", order_by="creation asc")
	return [
		filter_field("status", _("Status"), "Select", [(status, _(status)) for status in statuses]),
		*question_fields(form_questions(event, PROPOSAL_FORM_DOCTYPE)),
	]


def proposal_form(event):
	"""The event's talk proposal form — the Buzz Form its public submission page is served from."""
	return event_form(event.name, PROPOSAL_FORM_DOCTYPE)


def proposal_link(event) -> str | None:
	"""Where talks are proposed: the event's own form page, the route the dashboard serves."""
	form = proposal_form(event)
	return f"/b/{event.route}/{form.route}" if form and event.route else None


def are_proposals_closed(event) -> bool:
	form = proposal_form(event)
	return form.is_closed if form else True


def set_proposal_state(event: str, closed: bool) -> ProposalState:
	"""Open or close talk proposals, and answer with the state the server ends up in.

	Closure is the form's own, the same one the form page reads, so there is one mechanism.
	"""
	if not has_section_permission(event, "talks", "write", frappe.session.user):
		CannotManageEvent.throw()

	form = proposal_form(frappe.get_cached_doc("Buzz Event", str(event)))
	if not form:
		ProposalFormMissing.throw()

	form.set_closed(closed)
	return ProposalState(proposals_closed=form.is_closed)


def proposal_search_filters(search: str | None, event: str | None = None) -> list[list] | None:
	"""Title, or the name or email of a listed speaker — what a manager reads off the card."""
	term = (search or "").strip()
	if not term:
		return None

	pattern = f"%{term}%"
	speaker = frappe.qb.DocType("Proposal Speaker")
	match_condition = (
		speaker.first_name.like(pattern) | speaker.last_name.like(pattern) | speaker.email.like(pattern)
	)
	query = (
		frappe.qb.from_(speaker)
		.select(speaker.parent)
		.distinct()
		.where((speaker.parenttype == "Talk Proposal") & match_condition)
	)
	if event:
		proposal = frappe.qb.DocType("Talk Proposal")
		query = query.join(proposal).on(proposal.name == speaker.parent).where(proposal.event == str(event))
	matched_speakers = query.run(pluck=True)
	return [
		["title", "like", pattern],
		# A proposal with no matching speaker still has to fail this arm, and an empty
		# `in` list is what does that.
		["name", "in", matched_speakers],
	]


def proposal_trend(event: str, days: int = TREND_DAYS) -> ProposalTrend:
	"""Proposals submitted per day, oldest day first, with the all-time status split.

	Every day of the window is zero-filled: the series is read as a shape, and a missing
	row would draw as a shorter week rather than a quiet one.
	"""
	doc = ensure_event_team_access(event, "talks")
	event_id = str(doc.name)

	days = max(2, min(int(days), 90))
	window = [add_days(getdate(), -offset) for offset in reversed(range(days))]
	counted = submissions_by_day(event_id, window[0])
	status_rows = counts_by_status(event_id)

	return ProposalTrend(
		total=sum(row.count for row in status_rows),
		per_day=[DailySubmissions(date=day, count=counted.get(day, 0)) for day in window],
		by_status=[StatusTotal(status=str(row.status), count=row.count) for row in status_rows],
	)


def submissions_by_day(event: str, since) -> dict:
	"""Counts keyed by day, in one grouped query."""
	proposal = frappe.qb.DocType("Talk Proposal")
	day = Date(proposal.creation)
	rows = (
		frappe.qb.from_(proposal)
		.select(day.as_("day"), Count("*").as_("count"))
		.where((proposal.event == event) & (proposal.creation >= since))
		.groupby(day)
	).run(as_dict=True)
	return {getdate(row.day): row.count for row in rows}


def counts_by_status(event: str) -> list:
	"""An event's proposals counted per status, in one grouped query."""
	proposal = frappe.qb.DocType("Talk Proposal")
	return (
		frappe.qb.from_(proposal)
		.select(proposal.status, Count("*").as_("count"))
		.where(proposal.event == event)
		.groupby(proposal.status)
	).run(as_dict=True)


ACCEPTED = "Accepted"


def accept_proposal(proposal: str) -> AcceptedProposal:
	"""Accept a proposal, and put the talk it becomes on the event's programme.

	`create_talk` is the only path that builds the Event Talk and the speaker accounts,
	and the Desk button that used to be its only caller hides once the status reads
	Accepted — so a status written straight to Accepted stranded the proposal with no
	programme entry and no way back to make one.
	"""
	doc = frappe.get_doc("Talk Proposal", proposal)
	if not derived_has_permission(doc, ptype="write"):
		# A listed speaker holds write on their own proposal, which is not the same thing.
		frappe.throw(_("Only the event's team can accept a proposal."), frappe.PermissionError)

	existing = frappe.db.get_value("Event Talk", {"proposal": doc.name}, "name")
	if not existing:
		return AcceptedProposal(proposal=doc.name, talk=str(doc.create_talk().name), status=doc.status)

	# Accepted once already and moved away since: the talk stands, only the status returns.
	doc.status = ACCEPTED
	doc.save()
	return AcceptedProposal(proposal=doc.name, talk=str(existing), status=doc.status)
