import frappe

from buzz.events.doctype.buzz_form.form_types import (
	ATTENDEE_FORM_DOCTYPE,
	ATTENDEE_ROUTE,
	REGISTRATION_FORM_DOCTYPE,
)


def execute():
	"""Registration forms gain rows for their core fields, so the builder can order and rename them."""
	add_missing_attendee_forms()
	forms = frappe.get_all(
		"Buzz Form",
		filters={"form_doctype": ["in", [REGISTRATION_FORM_DOCTYPE, ATTENDEE_FORM_DOCTYPE]]},
		pluck="name",
	)
	for name in forms:
		doc = frappe.get_doc("Buzz Form", name)
		# Older forms may break rules added since, and must still gain the rows.
		doc.flags.ignore_validate = doc.flags.ignore_links = True
		doc.sync_standard_rows()
		doc.validate_standard_rows()
		doc.save(ignore_permissions=True)


def add_missing_attendee_forms():
	"""Events made before the attendee form existed have only the registration form."""
	with_attendee_form = frappe.get_all(
		"Buzz Form", filters={"form_doctype": ATTENDEE_FORM_DOCTYPE}, pluck="event"
	)
	for event in frappe.get_all(
		"Buzz Form",
		filters={"form_doctype": REGISTRATION_FORM_DOCTYPE, "event": ["not in", with_attendee_form or [""]]},
		pluck="event",
	):
		form = frappe.get_doc(
			{
				"doctype": "Buzz Form",
				"title": "Attendee details",
				"event": event,
				"form_doctype": ATTENDEE_FORM_DOCTYPE,
				"route": ATTENDEE_ROUTE,
				"publish": 0,
			}
		)
		form.flags.migrating = True
		form.insert(ignore_permissions=True)
