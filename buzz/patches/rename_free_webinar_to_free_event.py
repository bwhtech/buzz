import frappe
from frappe.model.utils.rename_field import rename_field

DOCTYPES = ("Buzz Event", "Event Proposal")
OLD_FIELD = "free_webinar"
NEW_FIELD = "free_event"


def execute():
	"""The flag applies to any Zoom-backed event, not just webinars.

	Both doctypes rename together: Event Proposal maps onto Buzz Event through
	get_mapped_doc, which matches on fieldname, so a half-rename would silently
	stop carrying the flag over. The old column is left for `bench trim-tables`.
	"""
	for doctype in DOCTYPES:
		if frappe.db.has_column(doctype, OLD_FIELD):
			rename_field(doctype, OLD_FIELD, NEW_FIELD)
