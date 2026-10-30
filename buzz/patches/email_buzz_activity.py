import frappe
from frappe.utils.fixtures import sync_fixtures

from buzz.subscriptions import NOTIFICATION_TYPE


def execute():
	"""Frappe emails a notification only for types in the user's Notification Settings, and
	seeds those only when the user is created, so users from before Buzz Activity lack it."""
	sync_fixtures("buzz")
	for name in frappe.get_all("Notification Settings", pluck="name"):
		settings = frappe.get_doc("Notification Settings", name)
		types = {row.notification_type for row in settings.email_notification_types}
		# An empty list means the user turned off every notification email.
		if types and NOTIFICATION_TYPE not in types:
			settings.append("email_notification_types", {"notification_type": NOTIFICATION_TYPE})
			settings.save(ignore_permissions=True)
