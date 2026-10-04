import frappe


def execute():
	"""Event Host names used to be the docname. `host_name` now carries the label."""
	host = frappe.qb.DocType("Event Host")
	frappe.qb.update(host).set(host.host_name, host.name).where(
		(host.host_name.isnull()) | (host.host_name == "")
	).run()
