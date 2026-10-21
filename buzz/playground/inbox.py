import base64
import email
from email import policy
from email.message import EmailMessage
from html import escape

import frappe
from frappe import safe_encode
from frappe.email.doctype.email_queue.email_queue import SendMailContext

from buzz.playground import is_playground, sandbox_of


def capture_email(queue, method=None):
	"""Copy each queued email into the Playground Inbox instead of sending it."""
	if not is_playground():
		return

	if not frappe.flags.seeding_playground:
		try:
			for recipient in queue.recipients:
				CapturedEmail(queue, recipient.recipient).save()
		except Exception:
			frappe.log_error("Playground email capture failed", reference_doctype="Email Queue")

	# Muted mail stays "Not Sent" forever; unmuting the site later would deliver the backlog.
	queue.db_set("status", "Cancelled", update_modified=False)


class CapturedEmail:
	def __init__(self, queue, recipient: str):
		self.queue = queue
		self.recipient = recipient
		self.message: EmailMessage = email.message_from_bytes(self.build(), policy=policy.default)

	def build(self) -> bytes:
		try:
			return SendMailContext(self.queue).build_message(self.recipient)
		except Exception:
			# Keep the email, minus the attachments that failed to render.
			frappe.log_error("Playground email attachments failed", reference_doctype="Email Queue")
			return safe_encode(self.queue.message)

	def save(self):
		doc = frappe.get_doc(
			{
				"doctype": "Playground Email",
				"sandbox": self.sandbox(),
				"subject": str(self.message["Subject"] or ""),
				"sender": self.queue.sender,
				"recipient": self.recipient,
				"reference_doctype": self.queue.reference_doctype,
				"reference_name": self.queue.reference_name,
				"message": self.body(),
			}
		).insert(ignore_permissions=True)
		self.save_attachments(doc.name)
		self.notify(doc)

	def body(self) -> str:
		part = self.message.get_body(preferencelist=("html", "plain"))
		if not part:
			return ""
		content = part.get_content()
		if part.get_content_subtype() != "html":
			return f"<pre>{escape(content)}</pre>"
		return self.inline_images(content)

	def inline_images(self, html: str) -> str:
		"""The inbox frame cannot resolve `cid:` links, so inline images go in as data URIs."""
		for part in self.message.walk():
			if (content_id := part.get("Content-ID")) and (payload := part.get_payload(decode=True)):
				data = base64.b64encode(payload).decode()
				html = html.replace(
					f"cid:{content_id.strip('<>')}", f"data:{part.get_content_type()};base64,{data}"
				)
		return html

	def save_attachments(self, email_name: str):
		for part in self.message.iter_attachments():
			file = {
				"doctype": "File",
				"file_name": part.get_filename() or "attachment",
				"content": part.get_payload(decode=True),
				"attached_to_doctype": "Playground Email",
				"attached_to_name": email_name,
				"is_private": 1,
			}
			# The visitor cannot write to Playground Email, which File checks for attachments.
			frappe.get_doc(file).insert(ignore_permissions=True)

	def sandbox(self) -> str | None:
		return sandbox_of(self.queue.owner) or self.sandbox_of_reference()

	def sandbox_of_reference(self) -> str | None:
		doctype, name = self.queue.reference_doctype, self.queue.reference_name
		if not (doctype and name and frappe.db.exists(doctype, name)):
			return None
		doc = frappe.get_doc(doctype, name)
		team = doc.get("team") or (doc.get("event") and frappe.db.get_value("Buzz Event", doc.event, "team"))
		return team and frappe.db.get_value("Playground Sandbox", {"team": team})

	def notify(self, doc):
		if not doc.sandbox:
			return
		for user in frappe.get_doc("Playground Sandbox", doc.sandbox).personas:
			frappe.publish_realtime("playground_email", {"name": doc.name}, user=user, after_commit=True)
