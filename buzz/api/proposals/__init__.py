import frappe

from buzz.api.proposals import services
from buzz.api.proposals.schemas import (
	AcceptedProposal,
	EventProposalsResponse,
	ProposalListItem,
	ProposalTrend,
)


@frappe.whitelist()
def get_my_proposals() -> list[ProposalListItem]:
	"""Proposals where the session user is the submitter or a listed speaker."""
	return services.my_proposals()


@frappe.whitelist()
def get_event_proposals(
	event: str,
	search: str | None = None,
	statuses: str | None = None,
	order: str = "desc",
	start: int = 0,
	limit: int = services.PROPOSALS_PAGE_SIZE,
) -> EventProposalsResponse:
	"""One page of the talk proposals submitted to an event, for its team.

	`statuses` is comma-joined rather than a list: a GET query string carries one, and it
	is the same string the dashboard keeps the filter in.
	"""
	return services.event_proposals(event, search, statuses, order, start, limit)


@frappe.whitelist()
def get_event_proposal_trend(event: str, days: int = services.TREND_DAYS) -> ProposalTrend:
	"""Submissions per day for an event, for the card above its proposal list."""
	return services.proposal_trend(event, days)


@frappe.whitelist(methods=["POST"])
def accept_proposal(proposal: str) -> AcceptedProposal:
	"""Accept a proposal and create the Event Talk it becomes."""
	return services.accept_proposal(proposal)
