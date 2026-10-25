import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
from frappe.utils import get_url

from buzz.permissions import WRITE_ROLES
from buzz.subscriptions import NOTIFICATION_TYPE

PENDING_APPROVAL = {"requires_approval": 1, "docstatus": 0, "status": "Approval Pending"}


def approval_ticket_types(event: str) -> set[str]:
	names = frappe.get_all(
		"Event Ticket Type", filters={"event": event, "requires_approval": 1}, pluck="name"
	)
	return {str(name) for name in names}


def is_event_wide_approval(event: str) -> bool:
	return bool(frappe.db.get_value("Buzz Event", event, "requires_approval"))


def booking_needs_approval(event: str, ticket_types) -> bool:
	return is_event_wide_approval(event) or bool(
		approval_ticket_types(event) & {str(ticket_type) for ticket_type in ticket_types}
	)


def has_approval(event: str, except_ticket_type: str | None = None) -> bool:
	return is_event_wide_approval(event) or bool(approval_ticket_types(event) - {str(except_ticket_type)})


def has_priced_items(event: str, except_ticket_type: str | None = None) -> bool:
	names = frappe.get_all("Event Ticket Type", filters={"event": event}, pluck="name")
	names = [name for name in names if str(name) != str(except_ticket_type)]
	priced_ticket_type = names and frappe.db.exists(
		"Buzz Price", {"parenttype": "Event Ticket Type", "parent": ("in", names), "price": (">", 0)}
	)
	return bool(priced_ticket_type or frappe.db.exists("Ticket Add-on", {"event": event, "price": (">", 0)}))


def validate_free_only(
	event: str, approval_on: bool, priced: bool, except_ticket_type: str | None = None
) -> None:
	"""`approval_on` and `priced` describe the document being saved; the rest of the event is read from the database."""
	# Imported here: the booking package imports the ticket type controller that calls this.
	from buzz.api.booking.exceptions import ApprovalNeedsFreeTickets

	if approval_on and (priced or has_priced_items(event, except_ticket_type)):
		ApprovalNeedsFreeTickets.throw()
	if priced and has_approval(event, except_ticket_type):
		ApprovalNeedsFreeTickets.throw()


def notify_hosts_of_request(booking) -> None:
	event = frappe.get_cached_doc("Buzz Event", booking.event)
	members = frappe.get_all(
		"Buzz Team Membership",
		filters={"team": event.team, "enabled": 1, "team_role": ("in", sorted(WRITE_ROLES))},
		pluck="user",
	)
	emails = frappe.get_all("User", filters={"name": ("in", members)}, pluck="email") if members else []
	if not emails:
		return
	subject = _("{0} requested to join {1}").format(booking.buyer_name or booking.user, event.title)
	enqueue_create_notification(
		emails,
		{
			"type": NOTIFICATION_TYPE,
			"subject": subject,
			"from_user": booking.user,
			"document_type": booking.doctype,
			"document_name": booking.name,
			"link": get_url(f"/b/manage/events/{event.name}/guests?view=pending"),
			"email_content": subject,
		},
	)
