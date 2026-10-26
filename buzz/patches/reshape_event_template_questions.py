import frappe

from buzz.events.doctype.buzz_form.form_types import REGISTRATION_FORM_DOCTYPE

TABLE = "`tabEvent Template Custom Field`"


def execute():
	"""Name each template question's form; templates do not copy offline payment methods."""
	if not frappe.db.has_column("Event Template Custom Field", "applied_to"):
		return
	frappe.db.sql(f"delete from {TABLE} where applied_to = 'Offline Payment Form'")
	unmapped = "ifnull(form_doctype, '') = ''"
	for applied_to, asked_per in (("Booking", "Booking"), ("Ticket", "Attendee")):
		frappe.db.sql(
			f"update {TABLE} set form_doctype = %s, asked_per = %s where applied_to = %s and {unmapped}",
			(REGISTRATION_FORM_DOCTYPE, asked_per, applied_to),
		)
	frappe.db.sql(
		f"update {TABLE} set form_doctype = custom_form_doctype where applied_to = 'Custom Form' and {unmapped}"
	)
