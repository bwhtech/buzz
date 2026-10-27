import frappe
from frappe import _

from buzz.events.doctype.buzz_form.form_types import ATTENDEE_FORM_DOCTYPE, REGISTRATION_FORM_DOCTYPE

MOVED_APPLIED_TO = ("Booking", "Ticket", "Custom Form")


def execute():
	"""Registration and custom form questions now live on Buzz Forms; offline payment ones stay."""
	for row in moved_counts_by_form():
		questions = frappe.db.count("Buzz Form Field", {"parenttype": "Buzz Form", "parent": row.form})
		if not row.form or questions < row.moved:
			frappe.throw(
				_("Buzz Event {0}: {1} questions were not moved to its form.").format(
					row.event, row.form_doctype
				)
			)
	frappe.db.delete("Buzz Custom Field", {"applied_to": ["in", MOVED_APPLIED_TO]})


def moved_counts_by_form() -> list:
	if not frappe.db.has_column("Buzz Custom Field", "custom_form_doctype"):
		return []
	return frappe.db.sql(
		"""
		select moved.event, moved.form_doctype, moved.moved, form.name as form
		from (
			select event,
				case applied_to
					when 'Custom Form' then custom_form_doctype
					when 'Ticket' then %(attendee)s
					else %(registration)s
				end as form_doctype,
				count(*) as moved
			from `tabBuzz Custom Field`
			where applied_to in %(applied_to)s
			group by 1, 2
		) moved
		# Rows of a deleted event have no form to move to; they are deleted with the rest.
		join `tabBuzz Event` event on event.name = moved.event
		left join `tabBuzz Form` form on form.event = moved.event and form.form_doctype = moved.form_doctype
		""",
		{
			"registration": REGISTRATION_FORM_DOCTYPE,
			"attendee": ATTENDEE_FORM_DOCTYPE,
			"applied_to": MOVED_APPLIED_TO,
		},
		as_dict=True,
	)
