import frappe
from frappe.query_builder.functions import Count, Date
from frappe.utils import add_days, getdate

from buzz.api.events.services import ensure_event_team_access
from buzz.api.proposals.schemas import (
	DailySubmissions,
	EventProposalsResponse,
	ProposalListItem,
	ProposalSpeakerItem,
	ProposalTrend,
	StatusTotal,
)
from buzz.permissions import has_team_access

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
	"event.venue",
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
	)

	speakers = speakers_by_proposal([row.name for row in rows])

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
	statuses: str | None = None,
	order: str = "desc",
	start: int = 0,
	limit: int = PROPOSALS_PAGE_SIZE,
) -> EventProposalsResponse:
	"""One page of the talk proposals submitted to an event, newest first by default.

	Read access to the event's team is the bar, the same one its guest list uses.
	"""
	ensure_event_team_access(event)

	filters: dict = {"event": event}
	chosen = [status for status in (statuses or "").split(",") if status.strip()]
	if chosen:
		filters["status"] = ["in", chosen]
	or_filters = proposal_search_filters(search)
	limit = max(1, min(int(limit), 100))
	start = max(0, int(start))
	# Interpolated into ORDER BY, so it can only ever be one of two literals.
	direction = "asc" if str(order).lower() == "asc" else "desc"

	rows = frappe.get_all(
		"Talk Proposal",
		filters=filters,
		or_filters=or_filters,
		fields=PROPOSAL_LIST_FIELDS,
		order_by=f"creation {direction}, name {direction}",
		limit_start=start,
		limit_page_length=limit,
		ignore_permissions=True,
	)
	speakers = speakers_by_proposal([row.name for row in rows])

	total = frappe.db.count("Talk Proposal", {"event": event})
	matched = count_proposals(filters, or_filters) if or_filters or chosen else total
	title, team = frappe.db.get_value("Buzz Event", event, ["title", "team"])
	return EventProposalsResponse(
		title=title,
		total=total,
		matched=matched,
		proposals=[ProposalListItem(**row, speakers=speakers.get(row.name, [])) for row in rows],
		has_next_page=start + len(rows) < matched,
		can_write=has_team_access(team, "write", frappe.session.user),
	)


def proposal_search_filters(search: str | None) -> list[list] | None:
	"""Title, or the name or email of a listed speaker — what a manager reads off the card."""
	term = (search or "").strip()
	if not term:
		return None

	matched_speakers = frappe.get_all(
		"Proposal Speaker",
		filters={"parenttype": "Talk Proposal"},
		or_filters=[
			["first_name", "like", f"%{term}%"],
			["last_name", "like", f"%{term}%"],
			["email", "like", f"%{term}%"],
		],
		pluck="parent",
	)
	return [
		["title", "like", f"%{term}%"],
		# A proposal with no matching speaker still has to fail this arm, and an empty
		# `in` list is what does that.
		["name", "in", matched_speakers],
	]


def count_proposals(filters: dict, or_filters: list[list] | None) -> int:
	return len(
		frappe.get_all(
			"Talk Proposal",
			filters=filters,
			or_filters=or_filters,
			pluck="name",
			ignore_permissions=True,
		)
	)


def proposal_trend(event: str, days: int = TREND_DAYS) -> ProposalTrend:
	"""Proposals submitted per day, oldest day first, with the all-time status split.

	Every day of the window is zero-filled: the series is read as a shape, and a missing
	row would draw as a shorter week rather than a quiet one.
	"""
	ensure_event_team_access(event)

	days = max(2, min(int(days), 90))
	window = [add_days(getdate(), -offset) for offset in reversed(range(days))]
	counted = submissions_by_day(event, window[0])

	return ProposalTrend(
		total=frappe.db.count("Talk Proposal", {"event": event}),
		per_day=[DailySubmissions(date=day, count=counted.get(day, 0)) for day in window],
		by_status=[StatusTotal(status=str(row.status), count=row.count) for row in counts_by_status(event)],
	)


def submissions_by_day(event: str, since) -> dict:
	"""Counts keyed by day, in one grouped query."""
	proposal = frappe.qb.DocType("Talk Proposal")
	day = Date(proposal.creation)
	rows = (
		frappe.qb.from_(proposal)
		.select(day.as_("day"), Count("*").as_("count"))
		.where((proposal.event == event) & (day >= since))
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
