from collections import defaultdict

import frappe
from frappe.utils import parse_addr

from buzz.comments import team_members, team_of
from buzz.subscriptions import Subscriptions

TALK = "Talk Proposal"


def execute():
	"""Subscribes current team members who wrote a note on, or emailed from, a talk before
	subscriptions existed. An existing row, such as an unsubscribe, is kept."""
	for proposal, users in participants().items():
		subscriptions = Subscriptions(TALK, proposal)
		for user in users & set(team_members(team_of(TALK, proposal))):
			subscriptions.follow(user)


def participants() -> dict[str, set[str]]:
	by_proposal = defaultdict(set)
	notes = frappe.get_all(
		"Comment",
		filters={"reference_doctype": TALK, "comment_type": "Comment"},
		fields=["reference_name", "owner"],
	)
	for note in notes:
		by_proposal[note.reference_name].add(note.owner)
	for proposal, user in email_senders():
		by_proposal[proposal].add(user)
	return by_proposal


def email_senders() -> list[tuple[str, str]]:
	"""(talk, user) for each email a user sent from a talk."""
	emails = frappe.get_all(
		"Communication",
		filters={
			"reference_doctype": TALK,
			"communication_type": "Communication",
			"sent_or_received": "Sent",
		},
		fields=["reference_name", "sender"],
	)
	addresses = [parse_addr(email.sender)[1] for email in emails]
	if not addresses:
		return []
	users = dict(
		frappe.get_all("User", filters={"email": ("in", addresses)}, fields=["email", "name"], as_list=True)
	)
	return [
		(email.reference_name, users[address])
		for email, address in zip(emails, addresses, strict=True)
		if address in users
	]
