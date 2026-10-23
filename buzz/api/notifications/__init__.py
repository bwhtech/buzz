import frappe

from buzz.api.notifications.schemas import NotificationGroup
from buzz.api.notifications.services import NotificationInbox


@frappe.whitelist()
def get_notifications() -> list[NotificationGroup]:
	"""The session user's recent notifications, one group per record, newest first."""
	return NotificationInbox(frappe.session.user).groups()


@frappe.whitelist(methods=["POST"])
def mark_as_read(reference_doctype: str, reference_name: str) -> None:
	NotificationInbox(frappe.session.user).mark_as_read(reference_doctype, reference_name)
