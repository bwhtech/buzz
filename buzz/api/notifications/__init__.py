import frappe

from buzz.api.notifications.schemas import Notification
from buzz.api.notifications.services import NotificationInbox


@frappe.whitelist()
def get_notifications() -> list[Notification]:
	"""The session user's recent notifications, newest first."""
	return NotificationInbox(frappe.session.user).notifications()


@frappe.whitelist(methods=["POST"])
def mark_as_read(name: str) -> None:
	NotificationInbox(frappe.session.user).mark_as_read({"name": name})


@frappe.whitelist(methods=["POST"])
def mark_all_as_read() -> None:
	NotificationInbox(frappe.session.user).mark_as_read()
