import frappe

from buzz.api.notifications.schemas import NotificationEntry, NotificationGroup
from buzz.subscriptions import NOTIFICATION_TYPE, Subscriptions

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
	"""One user's Buzz notifications, grouped by the record they happened on."""

	def __init__(self, user: str):
		self.user = user
		self.filters = {"for_user": user, "type": NOTIFICATION_TYPE}

	def groups(self) -> list[NotificationGroup]:
		logs = frappe.get_all(
			"Notification Log", filters=self.filters, fields=LOG_FIELDS, order_by="creation desc", limit=LIMIT
		)
		actors = Actors(logs)
		by_record: dict[tuple, list] = {}
		for log in logs:
			by_record.setdefault((log.document_type, log.document_name), []).append(log)
		return [self.group(reference, rows, actors) for reference, rows in by_record.items()]

	def group(self, reference: tuple, logs: list, actors: "Actors") -> NotificationGroup:
		doctype, name = reference
		record = frappe.db.get_value(doctype, name, ["title", "event"], as_dict=True) or {}
		return NotificationGroup(
			reference_doctype=doctype,
			reference_name=name,
			title=record.get("title"),
			event_title=frappe.db.get_value("Buzz Event", record.get("event"), "title"),
			link=logs[0].link,
			subscribed=Subscriptions(doctype, name).is_subscribed(self.user),
			notifications=[actors.entry(log) for log in logs],
		)

	def mark_as_read(self, reference_doctype: str, reference_name: str) -> None:
		filters = {**self.filters, "document_type": reference_doctype, "document_name": reference_name}
		frappe.db.set_value("Notification Log", {**filters, "read": 0}, "read", 1, update_modified=False)


class Actors:
	"""Who wrote each note or email, looked up once for the whole list. A reply's sender
	is a speaker, who may have no user account."""

	def __init__(self, logs: list):
		users = [log.from_user for log in logs if log.from_user]
		emails = [log.source_name for log in logs if log.source_doctype == "Communication"]
		self.users = rows_by_name("User", users, ["full_name", "user_image"])
		self.emails = rows_by_name("Communication", emails, ["sender", "sender_full_name"])

	def entry(self, log) -> NotificationEntry:
		user = self.users.get(log.from_user)
		email = self.emails.get(log.source_name)
		return NotificationEntry(
			name=log.name,
			kind="reply" if email else "comment",
			actor=self.name_of(user, email) or log.from_user or "",
			actor_image=user.user_image if user else None,
			snippet=log.email_content,
			creation=log.creation,
			read=bool(log.read),
		)

	@staticmethod
	def name_of(user, email) -> str | None:
		if email:
			return email.sender_full_name or email.sender
		return user.full_name if user else None


def rows_by_name(doctype: str, names: list[str], fields: list[str]) -> dict:
	if not names:
		return {}
	rows = frappe.get_all(doctype, filters={"name": ("in", names)}, fields=["name", *fields])
	return {row.name: row for row in rows}
