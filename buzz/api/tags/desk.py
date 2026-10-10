import frappe
from frappe import _
from frappe.desk.doctype.tag import tag as frappe_tags

from buzz.api.tags.services import DocumentTags, create_team_tag, is_taggable
from buzz.events.doctype.buzz_tag.buzz_tag import document_team

# Desk's tag editor, routed to Buzz Tags on taggable records and to Frappe's tags everywhere else.


@frappe.whitelist()
def add_tag(tag: str, dt: str, dn: str, color: str | None = None):
	if not is_taggable(dt):
		return frappe_tags.add_tag(tag, dt, dn, color)
	tags = DocumentTags(dt, dn)
	added = create_team_tag(document_team(dt, dn), dt, tag)
	tags.replace([*tags.names(), added.name])
	return added.label


@frappe.whitelist()
def add_tags(tags: str | list[str], dt: str, docs: str | list[str], color: str | None = None):
	if not is_taggable(dt):
		return frappe_tags.add_tags(tags, dt, docs, color)
	if not frappe.get_cached_value("User", frappe.session.user, "bulk_actions"):
		frappe.throw(_("You are not allowed to perform bulk actions"), frappe.PermissionError)
	for doc in frappe.parse_json(docs):
		for tag in frappe.parse_json(tags):
			add_tag(tag, dt, doc)


@frappe.whitelist()
def remove_tag(tag: str, dt: str, dn: str):
	if not is_taggable(dt):
		return frappe_tags.remove_tag(tag, dt, dn)
	tags = DocumentTags(dt, dn)
	removed = frappe.db.get_value(
		"Buzz Tag", {"team": document_team(dt, dn), "document_type": dt, "label": tag}
	)
	tags.replace([name for name in tags.names() if name != removed])


@frappe.whitelist()
def get_tags(doctype: str, txt: str):
	if not is_taggable(doctype):
		return frappe_tags.get_tags(doctype, txt)
	filters = {"document_type": doctype, "label": ["like", f"%{txt}%"]}
	return sorted(set(frappe.get_list("Buzz Tag", filters=filters, pluck="label")))
