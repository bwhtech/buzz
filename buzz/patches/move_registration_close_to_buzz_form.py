import frappe

from buzz.events.doctype.buzz_form.form_types import REGISTRATION_FORM_DOCTYPE


def execute():
	if not frappe.db.has_column("Buzz Event", "registrations_close_at"):
		return
	cutoffs = frappe.db.sql(
		"select name, registrations_close_at from `tabBuzz Event` where registrations_close_at is not null",
		as_dict=True,
	)
	for event in cutoffs:
		form = frappe.db.get_value(
			"Buzz Form", {"event": event.name, "form_doctype": REGISTRATION_FORM_DOCTYPE}
		)
		if not form:
			print(f"Buzz Event {event.name} has no registration form; cutoff not moved")
			continue
		frappe.db.set_value(
			"Buzz Form", form, "auto_close_at", event.registrations_close_at, update_modified=False
		)
