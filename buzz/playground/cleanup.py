import frappe
from frappe.utils import now_datetime

from buzz.playground import is_playground, sandbox_teams


def delete_expired_sandboxes():
	if not is_playground():
		return
	expired = frappe.get_all(
		"Playground Sandbox", filters={"expires_on": ["<", now_datetime()]}, pluck="name"
	)
	for sandbox in expired:
		try:
			delete_sandbox(sandbox)
			# One sandbox per transaction, so a failure skips only that sandbox.
			frappe.db.commit()  # nosemgrep: frappe-manual-commit
		except Exception:
			frappe.db.rollback()
			frappe.log_error("Playground sandbox cleanup failed", reference_doctype="Playground Sandbox")


def delete_sandbox(name: str):
	"""Remove a sandbox and everything its team made.

	Raw deletes, because bookings and tickets are submitted and `delete_doc` refuses them.
	"""
	sandbox = frappe.get_doc("Playground Sandbox", name)
	teams = sandbox_teams(sandbox)
	events = frappe.get_all("Buzz Event", filters={"team": ["in", teams]}, pluck="name")
	delete_records_linked_to("Buzz Event", events)
	delete_records_linked_to("Buzz Team", teams)
	delete_records("Buzz Team", teams)
	delete_records("Playground Email", frappe.get_all("Playground Email", {"sandbox": name}, pluck="name"))
	sandbox.delete(ignore_permissions=True)
	for user in sandbox.personas:
		frappe.delete_doc("User", user, force=True, ignore_permissions=True)


# Only direct links to the event or team; records two hops away (payments) stay behind.
def delete_records_linked_to(doctype: str, names: list):
	if not names:
		return
	links = frappe.get_all(
		"DocField", filters={"fieldtype": "Link", "options": doctype}, fields=["parent", "fieldname"]
	)
	for link in links:
		meta = frappe.get_meta(link.parent)
		if meta.istable or meta.issingle or link.parent == "Playground Sandbox":
			continue
		delete_records(
			link.parent, frappe.get_all(link.parent, {link.fieldname: ["in", names]}, pluck="name")
		)


def delete_records(doctype: str, names: list):
	if not names:
		return
	files = frappe.get_all(
		"File", filters={"attached_to_doctype": doctype, "attached_to_name": ["in", names]}, pluck="name"
	)
	for table in frappe.get_meta(doctype).get_table_fields():
		frappe.db.delete(table.options, {"parent": ["in", names], "parenttype": doctype})
	frappe.db.delete(doctype, {"name": ["in", names]})
	# After the records: File refuses to delete while a record's Attach field still points to it.
	for file in files:
		frappe.delete_doc("File", file, ignore_permissions=True)
