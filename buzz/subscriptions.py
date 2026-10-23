import frappe
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
from frappe.model.document import Document

DOCTYPE = "Buzz Notification Subscription"
NOTIFICATION_TYPE = "Buzz Activity"


class Subscriptions:
	"""Who hears about activity on one record. A row with `subscribed = 0` remembers an
	unsubscribe, so being mentioned does not re-subscribe the user."""

	def __init__(self, reference_doctype: str, reference_name: str):
		self.reference = {"reference_doctype": reference_doctype, "reference_name": reference_name}

	def row(self, user: str) -> str | None:
		return frappe.db.get_value(DOCTYPE, {**self.reference, "user": user})

	def subscribe(self, user: str) -> None:
		self.set(user, True)

	def unsubscribe(self, user: str) -> None:
		self.set(user, False)

	def follow(self, user: str) -> None:
		"""Subscribes the user unless they already chose."""
		if not self.row(user):
			self.subscribe(user)

	def set(self, user: str, subscribed: bool) -> None:
		if name := self.row(user):
			frappe.db.set_value(DOCTYPE, name, "subscribed", subscribed)
		else:
			frappe.get_doc(
				{"doctype": DOCTYPE, **self.reference, "user": user, "subscribed": subscribed}
			).insert(ignore_permissions=True)

	def is_subscribed(self, user: str) -> bool:
		return bool(frappe.db.get_value(DOCTYPE, {**self.reference, "user": user}, "subscribed"))

	def users(self) -> list[str]:
		return frappe.get_all(DOCTYPE, filters={**self.reference, "subscribed": 1}, pluck="user")

	def emails(self, skip: set[str]) -> list[str]:
		"""Frappe looks notification recipients up by email, which is not always the user's name."""
		users = [user for user in self.users() if user not in skip]
		return frappe.get_all("User", filters={"name": ("in", users)}, pluck="email") if users else []

	def notify(
		self,
		source: Document,
		subject: str,
		from_user: str | None,
		link: str | None,
		content: str | None = None,
		skip: set[str] = frozenset(),
	) -> None:
		"""`source` is the note or email that caused it. Frappe drops `from_user` itself and
		emails each user unless they turned this type off."""
		emails = self.emails(skip)
		if not emails:
			return
		enqueue_create_notification(
			emails,
			{
				"type": NOTIFICATION_TYPE,
				"subject": subject,
				"from_user": from_user,
				"document_type": self.reference["reference_doctype"],
				"document_name": self.reference["reference_name"],
				"link": link,
				"source_doctype": source.doctype,
				"source_name": source.name,
				"email_content": content,
			},
		)
