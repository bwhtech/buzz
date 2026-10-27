import frappe

from buzz.events.doctype.buzz_form.form_types import form_type


def execute():
	"""Hidden standard fields become disabled rows, so the form builder can order and rename them."""
	form = frappe.qb.DocType("Buzz Form")
	for name, excluded_fields in frappe.qb.from_(form).select(form.name, form.excluded_fields).run():
		doc = frappe.get_doc("Buzz Form", name)
		hide_excluded_fields(doc, excluded_fields)
		# Older forms may break rules added since, and must still move.
		doc.flags.ignore_validate = doc.flags.ignore_links = True
		doc.save(ignore_permissions=True)


def hide_excluded_fields(doc, excluded_fields: str | None):
	hidden = {fieldname.strip() for fieldname in (excluded_fields or "").split(",") if fieldname.strip()}
	doc.sync_standard_rows()
	kind = form_type(doc.form_doctype)
	fields = kind.standard_fields(doc.form_doctype)
	for row in doc.questions:
		if not row.is_standard or row.fieldname not in hidden:
			continue
		# A field the form type now requires stays on, even where it used to be hidden.
		if not (fields[row.fieldname].reqd or row.fieldname in kind.locked_fieldnames):
			row.enabled = 0
	doc.validate_standard_rows()
