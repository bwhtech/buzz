import frappe
from werkzeug.wrappers import Response

from buzz.api.comments.schemas import ActivityEntry
from buzz.api.comments.services import DocumentComments, email_attachment
from buzz.api.teams.schemas import TeamMember


@frappe.whitelist()
def get_activity(reference_doctype: str, reference_name: str) -> list[ActivityEntry]:
	"""Notes, emails, tracked field changes and the record's creation, oldest first."""
	return DocumentComments(reference_doctype, reference_name).activity()


@frappe.whitelist()
def get_mention_members(reference_doctype: str, reference_name: str) -> list[TeamMember]:
	return DocumentComments(reference_doctype, reference_name).members()


@frappe.whitelist()
def get_email_sender(reference_doctype: str, reference_name: str) -> str | None:
	"""The address a note emailed from this record is sent from."""
	return DocumentComments(reference_doctype, reference_name).email_sender()


@frappe.whitelist()
def get_email_attachment(name: str) -> Response:
	return email_attachment(name)


@frappe.whitelist(methods=["POST"])
def add_comment(
	reference_doctype: str,
	reference_name: str,
	content: str,
	email_recipients: bool = False,
	cc: list[str] | None = None,
	bcc: list[str] | None = None,
) -> str:
	"""With `email_recipients`, the note is emailed to the record's outside party, such as its speakers,
	copying `cc` and `bcc`, instead of being kept as a team note."""
	return DocumentComments(reference_doctype, reference_name).add(content, email_recipients, cc, bcc)


@frappe.whitelist(methods=["POST"])
def delete_comment(name: str) -> None:
	DocumentComments.of_comment(name).delete(name)
