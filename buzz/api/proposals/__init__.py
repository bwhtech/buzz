from datetime import datetime

import frappe
from pydantic import BaseModel


class ProposalListItem(BaseModel):
	name: str
	title: str
	event: str
	event_title: str | None = None
	status: str
	creation: datetime


@frappe.whitelist()
def get_my_proposals() -> list[dict]:
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
		fields=["name", "title", "event", "event.title as event_title", "status", "creation"],
		order_by="creation desc",
	)

	return [ProposalListItem(**row).model_dump() for row in rows]
