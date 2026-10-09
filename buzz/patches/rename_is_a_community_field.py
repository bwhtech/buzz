import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	if frappe.db.has_column("Buzz Team", "is_a_community"):
		rename_field("Buzz Team", "is_a_community", "accept_community_submissions")
