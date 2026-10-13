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
def count_recipients(event: str, audience: str, filters: str | None = None) -> RecipientCount:
	"""How many people a message with these recipients would reach right now.

	`filters` is a JSON list of `[field, operator, value]`, the same the audience's list page sends.
	"""
	return services.count_recipients(event, audience, filters)


@frappe.whitelist(methods=["POST"])
def send_communication(
	event: str,
	audience: str,
	message: str,
	subject: str = "",
	filters: str = "",
	scheduled_at: datetime | None = None,
) -> CommunicationItem:
	"""Queue a message to the audience now, or at `scheduled_at`."""
	return services.send_communication(event, audience, message, subject, filters, scheduled_at)


@frappe.whitelist(methods=["POST"])
def update_support_email(event: str, support_email: str) -> None:
	"""Set the reply-to address for the team the event belongs to. Owner/Admin only."""
	services.update_support_email(event, support_email)
