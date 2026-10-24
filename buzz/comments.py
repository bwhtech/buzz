from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.desk.notifications import extract_mentions
from frappe.utils import get_fullname, get_url, strip_html

from buzz.subscriptions import Subscriptions

DASHBOARD_ROUTES = {"Talk Proposal": "/b/manage/events/{event}/talks?proposal={name}"}


def is_commentable(doctype: str | None) -> bool:
	return doctype in frappe.get_hooks("commentable_doctypes")


def team_of(doctype: str, name: str) -> str | None:
	if frappe.get_meta(doctype).has_field("team"):
		return frappe.db.get_value(doctype, name, "team")
	event = frappe.db.get_value(doctype, name, "event")
	return frappe.db.get_value("Buzz Event", event, "team") if event else None


def team_members(team: str | None) -> list[str]:
	if not team:
		return []
	return frappe.get_all("Buzz Team Membership", filters={"team": team, "enabled": 1}, pluck="user")


def publish_to_team(doctype: str, name: str) -> None:
	"""Tells open drawers to refetch, without carrying the note itself."""
	message = {"reference_doctype": doctype, "reference_name": name}
	for user in team_members(team_of(doctype, name)):
		frappe.publish_realtime("buzz_comment_update", message, user=user, after_commit=True)


def notify_team_of_email(doc, method=None) -> None:
	if not (is_commentable(doc.reference_doctype) and doc.reference_name):
		return
	publish_to_team(doc.reference_doctype, doc.reference_name)
	if doc.communication_type == "Communication" and doc.sent_or_received == "Received":
		notify_subscribers(doc, _("{0} replied on {1}"), doc.sender_full_name or doc.sender, from_user=None)


def notify_subscribers(
	source, subject: str, author: str, from_user: str | None, skip: set[str] = frozenset()
) -> None:
	"""Tells everyone following the note's or email's record, with a plain-text preview of it."""
	doctype, name = source.reference_doctype, source.reference_name
	title = frappe.db.get_value(doctype, name, "title")
	Subscriptions(doctype, name).notify(
		source,
		subject.format(author, title),
		from_user,
		dashboard_url(doctype, name, activity=source.name),
		content=snippet_of(source),
		skip=skip,
	)


def snippet_of(source) -> str:
	# Imported here: buzz.api.comments imports this module.
	from buzz.api.comments.email_content import SNIPPET_LENGTH, EmailContent

	if source.doctype == "Communication":
		return EmailContent(source.content).snippet()
	return " ".join(strip_html(source.content or "").split())[:SNIPPET_LENGTH]


class TeamComment:
	"""Keeps notes on team records within the team.

	Frappe broadcasts a comment to the document's realtime room and caches it on the document
	row; a speaker reads both for their own proposal.
	"""

	def is_team_note(self) -> bool:
		return self.comment_type == "Comment" and is_commentable(self.reference_doctype)

	def after_insert(self):
		if not self.is_team_note():
			return super().after_insert()
		mentioned = notify_mentioned_members(self)
		self.subscribe_participants(mentioned)
		notify_subscribers(
			self, _("{0} commented on {1}"), get_fullname(self.owner), from_user=self.owner, skip=mentioned
		)
		self.notify_change("add")

	def subscribe_participants(self, mentioned: set[str]):
		subscriptions = Subscriptions(self.reference_doctype, self.reference_name)
		subscriptions.subscribe(self.owner)
		for user in mentioned:
			subscriptions.follow(user)

	def on_update(self):
		if not self.is_team_note():
			return super().on_update()
		if not self.is_new():
			self.notify_change("update")

	def remove_comment_from_cache(self):
		if not self.is_team_note():
			super().remove_comment_from_cache()

	def notify_change(self, action: str):
		if not self.is_team_note():
			return super().notify_change(action)
		publish_to_team(self.reference_doctype, self.reference_name)


def notify_mentioned_members(comment) -> set[str]:
	"""Emails the team members a note mentions, and returns them."""
	members = set(team_members(team_of(comment.reference_doctype, comment.reference_name)))
	mentioned = (set(extract_mentions(comment.content)) & members) - {comment.owner}
	if not mentioned:
		return mentioned
	args = note_email_args(comment.reference_doctype, comment.reference_name, comment.owner, comment.content)
	frappe.sendmail(
		recipients=sorted(mentioned),
		subject=_("{0} mentioned you on {1}").format(args["author"], args["record_title"]),
		template="comment_mention",
		args={
			**args,
			"button_url": dashboard_url(
				comment.reference_doctype, comment.reference_name, activity=comment.name
			),
			"button_label": _("Open in Buzz"),
		},
		raw_html=True,
		add_css=False,
		reference_doctype=comment.reference_doctype,
		reference_name=comment.reference_name,
	)
	return mentioned


def note_email_args(doctype: str, name: str, author: str, note: str) -> dict:
	"""What the note emails render: the note, who wrote it, and the record and event it is on."""
	record = frappe.db.get_value(doctype, name, ["title", "event"], as_dict=True)
	return {
		"author": get_fullname(author),
		"note": note,
		"record_title": record.title,
		"event_doc": frappe.get_cached_doc("Buzz Event", record.event) if record.event else None,
	}


def dashboard_url(doctype: str, name: str, activity: str | None = None) -> str | None:
	"""`activity` is the note or email the link scrolls the record's activity to."""
	route = DASHBOARD_ROUTES.get(doctype)
	if not route:
		return None
	url = route.format(event=frappe.db.get_value(doctype, name, "event"), name=name)
	return get_url(f"{url}&{urlencode({'activity': activity})}" if activity else url)
