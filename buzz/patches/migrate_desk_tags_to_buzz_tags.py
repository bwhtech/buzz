import frappe

from buzz.api.tags.services import DocumentTags, create_team_tag
from buzz.events.doctype.buzz_tag.buzz_tag import document_team


def execute():
	"""Desk now shows a taggable record's Buzz Tags, so the Frappe tags it had become its team's Buzz Tags."""
	for doctype in frappe.get_hooks("taggable_doctypes"):
		records = frappe.get_all(doctype, {"_user_tags": ["is", "set"]}, ["name", "_user_tags"])
		for record in records:
			team = document_team(doctype, record.name)
			labels = [label for label in record._user_tags.split(",") if label.strip()]
			tags = DocumentTags(doctype, record.name)
			tags.replace([*tags.names(), *(create_team_tag(team, doctype, label).name for label in labels)])
