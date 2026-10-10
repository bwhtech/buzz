import frappe

from buzz.api.tags.schemas import TagItem
from buzz.api.tags.services import DocumentTags, create_team_tag


@frappe.whitelist(methods=["POST"])
def create_tag(team: str, document_type: str, label: str) -> TagItem:
	return create_team_tag(team, document_type, label)


@frappe.whitelist(methods=["POST"])
def set_tags(document_type: str, document_name: str, tags: list[str]) -> list[TagItem]:
	"""Replaces every tag on the record with `tags`, a list of Buzz Tag names."""
	return DocumentTags(document_type, document_name).replace(tags)
