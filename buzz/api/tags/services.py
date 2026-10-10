import frappe
from frappe.query_builder import DocType

from buzz.api.tags.exceptions import EmptyTagLabel, NotTaggable
from buzz.api.tags.schemas import TagItem


def is_taggable(document_type: str) -> bool:
	return document_type in frappe.get_hooks("taggable_doctypes")


def ensure_taggable(document_type: str):
	if not is_taggable(document_type):
		NotTaggable.throw()


def create_team_tag(team: str, document_type: str, label: str) -> TagItem:
	"""A team's tag for one kind of record. Asking for a label the team already has returns that tag."""
	ensure_taggable(document_type)
	label = " ".join(label.split())
	if not label:
		EmptyTagLabel.throw()
	values = {"team": team, "document_type": document_type, "label": label}
	tag = frappe.new_doc("Buzz Tag", **values)
	tag.check_permission("create")
	existing = frappe.db.get_value("Buzz Tag", values, ["name", "label"], as_dict=True)
	if existing:
		return TagItem(**existing)
	tag.insert()
	return TagItem(name=tag.name, label=tag.label)


def team_tags(team: str, document_type: str) -> list[TagItem]:
	rows = frappe.get_all(
		"Buzz Tag",
		filters={"team": team, "document_type": document_type},
		fields=["name", "label"],
		order_by="label asc",
		ignore_permissions=True,
	)
	return [TagItem(**row) for row in rows]


def tags_by_document(document_type: str, names: list) -> dict[str, list[TagItem]]:
	"""Tags on each of `names`, keyed by the name as a string: Buzz Event names are integers."""
	if not names:
		return {}
	link, tag = DocType("Buzz Tag Link"), DocType("Buzz Tag")
	rows = (
		frappe.qb.from_(link)
		.join(tag)
		.on(tag.name == link.tag)
		.select(link.document_name, tag.name, tag.label)
		.where((link.document_type == document_type) & link.document_name.isin([str(n) for n in names]))
		.orderby(tag.label)
	).run(as_dict=True)
	tags = {}
	for row in rows:
		tags.setdefault(row.document_name, []).append(TagItem(name=row.name, label=row.label))
	return tags


def refresh_user_tags(document_type: str, names: list) -> dict[str, list[TagItem]]:
	"""Copies tag labels into `_user_tags`, the column desk shows as a record's Tags."""
	tags = tags_by_document(document_type, names)
	for name in names:
		labels = ",".join(tag.label for tag in tags.get(str(name), []))
		frappe.db.set_value(document_type, name, "_user_tags", labels, update_modified=False)
	return tags


class DocumentTags:
	"""The tags on one record. Changing them takes write access to the record."""

	def __init__(self, document_type: str, document_name: str):
		ensure_taggable(document_type)
		frappe.has_permission(document_type, "write", doc=document_name, throw=True)
		self.filters = {"document_type": document_type, "document_name": document_name}

	def names(self) -> list[str]:
		return frappe.get_all("Buzz Tag Link", filters=self.filters, pluck="tag")

	def replace(self, tags: list[str]) -> list[TagItem]:
		current = set(self.names())
		if removed := current - set(tags):
			frappe.db.delete("Buzz Tag Link", {**self.filters, "tag": ("in", list(removed))})
		for tag in set(tags) - current:
			frappe.get_doc({"doctype": "Buzz Tag Link", "tag": tag, **self.filters}).insert(
				ignore_permissions=True
			)
		document_type, name = self.filters["document_type"], self.filters["document_name"]
		return refresh_user_tags(document_type, [name]).get(str(name), [])
