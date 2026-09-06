from datetime import datetime

import frappe

from buzz.api.communications import services
from buzz.api.communications.schemas import (
	CommunicationItem,
	EventCommunicationsResponse,
	RecipientCount,
)


@frappe.whitelist()
def get_event_communications(event: str) -> EventCommunicationsResponse:
	"""Everything sent for an event, newest first, with what the composer needs to offer."""
	return services.event_communications(event)


@frappe.whitelist()
def count_recipients(
	event: str, audience: str, ticket_types: str | None = None, statuses: str | None = None
) -> RecipientCount:
	"""How many people a message with these recipients would reach right now."""
	return services.count_recipients(event, audience, ticket_types, statuses)


@frappe.whitelist(methods=["POST"])
def send_communication(
	event: str,
	audience: str,
	message: str,
	subject: str = "",
	ticket_types: str = "",
	statuses: str = "",
	scheduled_at: datetime | None = None,
) -> CommunicationItem:
	"""Queue a message to the audience now, or at `scheduled_at`."""
	return services.send_communication(
		event, audience, message, subject, ticket_types, statuses, scheduled_at
	)


@frappe.whitelist(methods=["POST"])
def update_support_email(event: str, support_email: str) -> None:
	"""Set the reply-to address for the team the event belongs to. Owner/Admin only."""
	services.update_support_email(event, support_email)
