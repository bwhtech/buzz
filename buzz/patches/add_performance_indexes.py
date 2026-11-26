import frappe

ADDITIONAL_FIELD_VALUE_INDEX = "additional_field_value_lookup_idx"


def execute():
	index_definitions = [
		("Event Booking", ["event", "docstatus", "status"], None),
		("Event Booking", ["event", "request_type", "docstatus"], None),
		("Event Booking", ["event", "creation"], None),
		("Event Booking", ["user", "docstatus"], None),
		("Event Booking", ["coupon_code", "docstatus"], None),
		("Event Booking", ["access_code", "docstatus"], None),
		("Event Booking Attendee", ["ticket_type", "parent"], None),
		("Event Booking Attendee", ["parent", "ticket_type", "currency"], None),
		("Event Ticket", ["event", "docstatus", "creation"], None),
		("Event Ticket", ["event", "docstatus", "ticket_type"], None),
		("Event Ticket", ["ticket_type", "docstatus"], None),
		("Event Ticket", ["booking", "docstatus"], None),
		("Event Ticket", ["attendee_email", "docstatus", "event"], None),
		("Event Ticket Type", ["event", "is_published"], None),
		(
			"Event Payment",
			["reference_docname", "reference_doctype", "payment_gateway", "creation", "name"],
			"event_payment_ref_gateway_idx",
		),
		("Event Check In", ["event", "docstatus", "zone", "date", "ticket"], None),
		("Event Check In", ["ticket", "zone", "docstatus"], None),
		("Additional Field", ["parenttype", "parent"], None),
		("Ticket Add-on Value", ["parenttype", "parent"], None),
		("Buzz Price", ["parenttype", "parentfield", "parent"], None),
		("Ticket Hold", ["ticket_type", "expires_at"], None),
		("Ticket Hold", ["ip_address", "expires_at"], None),
		("Ticket Add-on", ["event", "enabled"], None),
		("Event Ticket Category", ["event", "sort_order"], None),
		("Buzz Form", ["event", "form_doctype"], None),
		("Offline Payment Method", ["event", "enabled"], None),
	]
	for doctype, fields, index_name in index_definitions:
		frappe.db.add_index(doctype, fields, index_name=index_name)
	existing = frappe.db.sql(
		"SHOW INDEX FROM `tabAdditional Field` WHERE Key_name = %s", (ADDITIONAL_FIELD_VALUE_INDEX,)
	)
	if not existing:
		frappe.db.sql_ddl(
			"ALTER TABLE `tabAdditional Field` "
			"ADD INDEX `additional_field_value_lookup_idx` "
			"(`parenttype`, `parentfield`, `fieldname`, `value`(64), `parent`)"
		)
