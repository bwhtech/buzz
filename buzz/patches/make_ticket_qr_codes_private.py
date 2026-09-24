import frappe


def execute():
	files = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Event Ticket", "attached_to_field": "qr_code", "is_private": 0},
		pluck="name",
	)
	for name in files:
		file = frappe.get_doc("File", name)
		file.is_private = 1
		try:
			file.save(ignore_permissions=True)
		except FileNotFoundError:
			frappe.clear_last_message()
			continue
