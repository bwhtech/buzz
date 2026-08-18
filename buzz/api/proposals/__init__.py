import frappe

from buzz.api.proposals import services
from buzz.api.proposals.schemas import ProposalListItem


@frappe.whitelist()
def get_my_proposals() -> list[ProposalListItem]:
	"""Proposals where the session user is the submitter or a listed speaker."""
	return services.my_proposals()
