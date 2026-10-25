import frappe

from buzz.api.notifications.schemas import Notification
from buzz.subscriptions import NOTIFICATION_TYPE

LIMIT = 50
LOG_FIELDS = [
	"name",
	"read",
	"creation",
	"from_user",
	"link",
	"document_type",
	"document_name",
	"source_doctype",
	"source_name",
	"email_content",
]


class NotificationInbox:
	"""One user's Buzz notifications."""

	def __init__(self, user: str):
		self.user = user
		self.filters = {"for_user": user, "type": NOTIFICATION_TYPE}

	def notifications(self) -> list[Notification]:
		logs = frappe.get_all(
			"Notification Log", filters=self.filters, fields=LOG_FIELDS, order_by="creation desc", limit=LIMIT
		)
		actors, records = Actors(logs), Records(logs)
		return [Notification(**actors.of(log), **records.of(log), **self.basics(log)) for log in logs]

	@staticmethod
	def basics(log) -> dict:
		return {
			"name": log.name,
			"snippet": log.email_content,
			"creation": log.creation,
			"read": bool(log.read),
			"reference_doctype": log.document_type,
			"reference_name": log.document_name,
			"link": log.link,
		}

	def mark_as_read(self, filters: dict | None = None) -> None:
		filters = {**self.filters, **(filters or {}), "read": 0}
		frappe.db.set_value("Notification Log", filters, "read", 1, update_modified=False)


class Actors:
	"""Who wrote each note or email, looked up once for the whole list. A reply's sender
	is a speaker, who may have no user account."""

	def __init__(self, logs: list):
		users = [log.from_user for log in logs if log.from_user]
		emails = [log.source_name for log in logs if log.source_doctype == "Communication"]
		self.users = rows_by_name("User", users, ["full_name", "user_image"])
		self.emails = rows_by_name("Communication", emails, ["sender", "sender_full_name"])

	def of(self, log) -> dict:
		if email := self.emails.get(log.source_name):
			return {"kind": "reply", "actor": email.sender_full_name or email.sender}
		user = self.users.get(log.from_user)
		return {
			"kind": "comment",
			"actor": (user and user.full_name) or log.from_user or "",
			"actor_image": user and user.user_image,
		}


class Records:
	"""The title and event of each record the notifications are about."""

	def __init__(self, logs: list):
		by_doctype: dict[str, set] = {}
		for log in logs:
			by_doctype.setdefault(log.document_type, set()).add(log.document_name)
		self.rows = {
			doctype: rows_by_name(doctype, list(names), record_fields(doctype))
			for doctype, names in by_doctype.items()
		}
		events = {row.event for rows in self.rows.values() for row in rows.values() if row.event}
		self.events = rows_by_name("Buzz Event", list(events), ["title"])

	def of(self, log) -> dict:
		record = self.rows.get(log.document_type, {}).get(log.document_name)
		event = record and self.events.get(record.event)
		return {"title": record and record.title, "event_title": event and event.title}


def record_fields(doctype: str) -> list[str]:
	meta = frappe.get_meta(doctype)
	return [field for field in ("title", "event") if meta.has_field(field)]


def rows_by_name(doctype: str, names: list[str], fields: list[str]) -> dict:
	if not names:
		return {}
	rows = frappe.get_all(doctype, filters={"name": ("in", names)}, fields=["name", *fields])
	return {row.name: row for row in rows}
