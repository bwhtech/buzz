import frappe

from buzz.api.comments.schemas import CommentItem
from buzz.api.comments.services import DocumentComments
from buzz.api.teams.schemas import TeamMember


@frappe.whitelist()
def get_comments(reference_doctype: str, reference_name: str) -> list[CommentItem]:
	return DocumentComments(reference_doctype, reference_name).list()


@frappe.whitelist()
def get_mention_members(reference_doctype: str, reference_name: str) -> list[TeamMember]:
	return DocumentComments(reference_doctype, reference_name).members()


@frappe.whitelist(methods=["POST"])
def add_comment(
	reference_doctype: str, reference_name: str, content: str, email_recipients: bool = False
) -> str:
	"""`email_recipients` also emails the note to the record's outside party, such as its speakers."""
	return DocumentComments(reference_doctype, reference_name).add(content, email_recipients)


@frappe.whitelist(methods=["POST"])
def delete_comment(name: str) -> None:
	DocumentComments.of_comment(name).delete(name)
