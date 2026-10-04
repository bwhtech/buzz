import frappe

from buzz.api.proposals import services
from buzz.api.proposals.schemas import (
	AcceptedProposal,
	EventProposalsResponse,
	ProposalListItem,
	ProposalState,
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
	filters: str | None = None,
	order: str = "desc",
	start: int = 0,
	limit: int = services.PROPOSALS_PAGE_SIZE,
) -> EventProposalsResponse:
	"""One page of the talk proposals submitted to an event, for its team.

	`filters` is a JSON list of `[field, operator, value]`, the string the dashboard keeps in its URL.
	"""
	return services.event_proposals(event, search, filters, order, start, limit)


@frappe.whitelist()
def get_event_proposal_trend(event: str, days: int = services.TREND_DAYS) -> ProposalTrend:
	"""Submissions per day for an event, for the card above its proposal list."""
	return services.proposal_trend(event, days)


@frappe.whitelist(methods=["POST"])
def accept_proposal(proposal: str) -> AcceptedProposal:
	"""Accept a proposal and create the Event Talk it becomes."""
	return services.accept_proposal(proposal)


@frappe.whitelist(methods=["POST"])
def set_proposal_state(event: str, closed: bool) -> ProposalState:
	"""Open or close an event's talk proposals, answering with the state that results."""
	return services.set_proposal_state(event, closed)
