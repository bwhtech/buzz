import frappe
from frappe import _


def execute():
	"""Hidden standard fields become disabled rows, so the form builder can order and rename them."""
	form = frappe.qb.DocType("Buzz Form")
	hidden_by_form = dict(frappe.qb.from_(form).select(form.name, form.excluded_fields).run())
	forms = [frappe.get_doc("Buzz Form", name) for name in hidden_by_form]
	for doc in forms:
		hide_excluded_fields(doc, hidden_by_form[doc.name])
	# The rows were checked above; older forms may break rules added since and must still move.
	for doc in forms:
		doc.flags.ignore_validate = doc.flags.ignore_links = True
		doc.save(ignore_permissions=True)


def hide_excluded_fields(doc, excluded_fields: str | None):
	hidden = {fieldname.strip() for fieldname in (excluded_fields or "").split(",") if fieldname.strip()}
	try:
		doc.sync_standard_rows()
		for row in doc.questions:
			if row.is_standard and row.fieldname in hidden:
				row.enabled = 0
		doc.validate_standard_rows()
	except Exception:
		frappe.throw(
			_("Could not move the hidden fields of form {0} on event {1}.").format(doc.name, doc.event)
		)
