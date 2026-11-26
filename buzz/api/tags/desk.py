import frappe
from frappe import _
from frappe.desk.doctype.tag import tag as frappe_tags

from buzz.api.tags.services import DocumentTags, create_team_tag, is_taggable, refresh_user_tags
from buzz.events.doctype.buzz_tag.buzz_tag import document_team

# Desk's tag editor, routed to Buzz Tags on taggable records and to Frappe's tags everywhere else.


@frappe.whitelist()
def add_tag(tag: str, dt: str, dn: str, color: str | None = None):
	if not is_taggable(dt):
		return frappe_tags.add_tag(tag, dt, dn, color)
	tags = DocumentTags(dt, dn)
	added = create_team_tag(document_team(dt, dn), dt, tag)
	current = set(tags.names())
	tags.replace([*current, added.name], current=current)
	return added.label


@frappe.whitelist()
def add_tags(tags: str | list[str], dt: str, docs: str | list[str], color: str | None = None):
	if not is_taggable(dt):
		return frappe_tags.add_tags(tags, dt, docs, color)
	if not frappe.get_cached_value("User", frappe.session.user, "bulk_actions"):
		frappe.throw(_("You are not allowed to perform bulk actions"), frappe.PermissionError)
	doc_list = [str(doc) for doc in frappe.parse_json(docs)]
	tag_labels = frappe.parse_json(tags)
	if not doc_list or not tag_labels:
		return
	existing_links = {
		(str(row.document_name), row.tag)
		for row in frappe.get_all(
			"Buzz Tag Link",
			filters={"document_type": dt, "document_name": ["in", doc_list]},
			fields=["document_name", "tag"],
		)
	}
	team_tag_cache: dict[tuple[str, str], str] = {}
	for doc in doc_list:
		DocumentTags(dt, doc)
		team = document_team(dt, doc)
		for label in tag_labels:
			key = (team, label)
			if key not in team_tag_cache:
				team_tag_cache[key] = create_team_tag(team, dt, label).name
			tag_name = team_tag_cache[key]
			if (doc, tag_name) not in existing_links:
				frappe.get_doc(
					{"doctype": "Buzz Tag Link", "tag": tag_name, "document_type": dt, "document_name": doc}
				).insert(ignore_permissions=True)
				existing_links.add((doc, tag_name))
	refresh_user_tags(dt, doc_list)


@frappe.whitelist()
def remove_tag(tag: str, dt: str, dn: str):
	if not is_taggable(dt):
		return frappe_tags.remove_tag(tag, dt, dn)
	tags = DocumentTags(dt, dn)
	removed = frappe.db.get_value(
		"Buzz Tag", {"team": document_team(dt, dn), "document_type": dt, "label": tag}
	)
	current = set(tags.names())
	tags.replace([name for name in current if name != removed], current=current)


@frappe.whitelist()
def get_tags(doctype: str, txt: str):
	if not is_taggable(doctype):
		return frappe_tags.get_tags(doctype, txt)
	filters = {"document_type": doctype, "label": ["like", f"%{txt}%"]}
	return frappe.get_list(
		"Buzz Tag",
		filters=filters,
		pluck="label",
		distinct=True,
		order_by="label asc",
		limit_page_length=50,
	)
