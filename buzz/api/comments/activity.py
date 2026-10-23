import frappe
from frappe.desk.form.load import get_comments
from frappe.utils import parse_addr, split_emails

from buzz.api.comments.email_content import EmailContent
from buzz.api.comments.schemas import ActivityEntry, EmailAttachment

# Field changes worth a line in the timeline, read from the record's Version history.
TRACKED_FIELDS = {"Talk Proposal": ["status"]}


class ActivityFeed:
	"""A record's notes, emails, tracked field changes and creation, oldest first."""

	def __init__(self, reference_doctype: str, reference_name: str):
		self.reference_doctype = reference_doctype
		self.reference_name = reference_name

	def entries(self) -> list[ActivityEntry]:
		rows = [*self.created(), *self.comments(), *self.emails(), *self.changes()]
		people = user_details({row["owner"] for row in rows})
		entries = [with_person(row, people.get(row["owner"])) for row in rows]
		return sorted(entries, key=lambda entry: entry.creation)

	def created(self) -> list[dict]:
		row = frappe.db.get_value(
			self.reference_doctype, self.reference_name, ["owner", "creation"], as_dict=True
		)
		return [{"name": str(self.reference_name), "kind": "created", **row}]

	def comments(self) -> list[dict]:
		return [
			{
				"name": row.name,
				"kind": "comment",
				"owner": row.owner,
				"creation": row.creation,
				"content": row.content,
			}
			for row in get_comments(self.reference_doctype, self.reference_name)
		]

	def emails(self) -> list[dict]:
		rows = frappe.get_all(
			"Communication",
			filters=self.reference_filters(
				"reference_doctype", "reference_name", communication_medium="Email"
			),
			fields=[
				"name",
				"creation",
				"content",
				"sender",
				"sender_full_name",
				"recipients",
				"cc",
				"sent_or_received",
			],
		)
		files = attached_files([row.name for row in rows])
		return [email_row(row, files.get(row.name, [])) for row in rows]

	def changes(self) -> list[dict]:
		fields = TRACKED_FIELDS.get(self.reference_doctype, [])
		rows = frappe.get_all(
			"Version",
			filters=self.reference_filters("ref_doctype", "docname"),
			fields=["name", "owner", "creation", "data"],
		)
		return [change for row in rows for change in field_changes(row, fields)]

	def reference_filters(self, doctype_field: str, name_field: str, **extra) -> dict:
		return {doctype_field: self.reference_doctype, name_field: str(self.reference_name), **extra}


def email_row(row, files: list) -> dict:
	sender_name, sender_email = parse_addr(row.sender)
	received = row.sent_or_received == "Received"
	# A reply carries the thread, a signature and the sender's styling; a sent note is our own.
	email = EmailContent(row.content)
	return {
		"name": row.name,
		"kind": "email",
		"owner": sender_email,
		"display_name": row.sender_full_name or sender_name,
		"creation": row.creation,
		"content": email.body() if received else row.content,
		"quoted_content": email.quoted_body() if received else None,
		"snippet": email.snippet(),
		"attachments": email_attachments(files, row.content or "", email.body_image_sources()),
		"recipients": split_emails(row.recipients or ""),
		"cc": split_emails(row.cc or ""),
		"received": received,
	}


def attached_files(communications: list[str]) -> dict[str, list]:
	rows = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Communication", "attached_to_name": ("in", communications)},
		fields=["attached_to_name", "file_name", "file_url", "file_size"],
		order_by="creation asc",
	)
	files: dict[str, list] = {}
	for row in rows:
		files.setdefault(row.attached_to_name, []).append(row)
	return files


def email_attachments(files: list, content: str, body_images: list[str]) -> list[EmailAttachment]:
	"""Attached files, plus images placed in the message; logos and banners in the signature or
	the quoted thread are left out."""
	return [
		EmailAttachment(name=file.file_name, url=file.file_url, size=file.file_size or 0)
		for file in files
		if file.file_url
		and (file.file_url not in content or any(source.startswith(file.file_url) for source in body_images))
	]


def field_changes(version, fields: list[str]) -> list[dict]:
	changed = frappe.parse_json(version.data).get("changed") or []
	return [
		{
			"name": f"{version.name}-{field}",
			"kind": "change",
			"owner": version.owner,
			"creation": version.creation,
			"field": field,
			"old_value": old,
			"new_value": new,
		}
		for field, old, new in changed
		if field in fields
	]


def user_details(users: set[str]) -> dict:
	rows = frappe.get_all(
		"User", filters={"name": ("in", list(users))}, fields=["name", "full_name", "user_image"]
	)
	return {row.name: row for row in rows}


def with_person(row: dict, user) -> ActivityEntry:
	fallback = row.pop("display_name", None) or row["owner"]
	return ActivityEntry(
		**row,
		owner_name=(user and user.full_name) or fallback,
		owner_image=user and user.user_image,
	)
