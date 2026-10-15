import frappe
from frappe import _
from frappe.desk.notifications import extract_mentions
from frappe.utils import escape_html, get_fullname, get_url

from buzz.emails import send_message_email

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
		notify_mentioned_members(self)
		self.notify_change("add")

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
		message = {"reference_doctype": self.reference_doctype, "reference_name": self.reference_name}
		for user in team_members(team_of(self.reference_doctype, self.reference_name)):
			frappe.publish_realtime("buzz_comment_update", message, user=user, after_commit=True)


def notify_mentioned_members(comment) -> None:
	members = set(team_members(team_of(comment.reference_doctype, comment.reference_name)))
	mentioned = (set(extract_mentions(comment.content)) & members) - {comment.owner}
	if not mentioned:
		return
	send_message_email(
		title=_("{0} mentioned you in a comment").format(get_fullname(comment.owner)),
		message=comment.content + open_link(comment.reference_doctype, comment.reference_name),
		recipients=sorted(mentioned),
		reference_doctype=comment.reference_doctype,
		reference_name=comment.reference_name,
	)


def open_link(doctype: str, name: str) -> str:
	route = DASHBOARD_ROUTES.get(doctype)
	if not route:
		return ""
	event = frappe.db.get_value(doctype, name, "event")
	url = get_url(route.format(event=event, name=name))
	return f'<p><a href="{escape_html(url)}">{_("Open in Buzz")}</a></p>'
