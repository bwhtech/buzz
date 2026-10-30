import frappe

from buzz.events.doctype.buzz_form.form_types import ATTENDEE_FORM_DOCTYPE, REGISTRATION_FORM_DOCTYPE


def execute():
	"""Name each template question's form; templates do not copy offline payment methods."""
	if not frappe.db.has_column("Event Template Custom Field", "applied_to"):
		return
	frappe.db.delete("Event Template Custom Field", {"applied_to": "Offline Payment Form"})
	for applied_to, form_doctype in (
		("Booking", REGISTRATION_FORM_DOCTYPE),
		("Ticket", ATTENDEE_FORM_DOCTYPE),
	):
		frappe.db.sql(
			"""update `tabEvent Template Custom Field` set form_doctype = %s
			where applied_to = %s and ifnull(form_doctype, '') = ''""",
			(form_doctype, applied_to),
		)
	frappe.db.sql(
		"""update `tabEvent Template Custom Field` set form_doctype = custom_form_doctype
		where applied_to = 'Custom Form' and ifnull(form_doctype, '') = ''"""
	)
