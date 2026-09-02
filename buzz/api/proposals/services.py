import frappe

from buzz.api.proposals.schemas import ProposalListItem, ProposalSpeakerItem


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
		fields=[
			"name",
			"title",
			"event",
			"event.title as event_title",
			"event.start_date",
			"event.end_date",
			"event.banner_image",
			"event.allow_editing_talks_after_acceptance",
			"status",
			"creation",
			"modified",
		],
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
