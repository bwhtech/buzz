from email import message_from_string

import frappe

from buzz.events.doctype.event_venue.map_link import MAP_LINK_CACHE_PREFIX


def clear_map_link_cache():
	frappe.cache.delete_keys(MAP_LINK_CACHE_PREFIX)


def queued_emails(communication: str) -> list:
	return frappe.get_all(
		"Email Queue",
		filters={"reference_doctype": "Event Communication", "reference_name": communication},
		fields=["name", "send_after", "message"],
	)


def queued_recipients(communication: str) -> set[str]:
	queue_names = [row.name for row in queued_emails(communication)]
	if not queue_names:
		return set()
	return set(
		frappe.get_all("Email Queue Recipient", filters={"parent": ["in", queue_names]}, pluck="recipient")
	)


def html_part(raw_message: str) -> str:
	"""The HTML body, decoded: the queue stores it quoted-printable, wrapped at 76 columns."""
	for part in message_from_string(raw_message).walk():
		if part.get_content_type() == "text/html":
			return part.get_payload(decode=True).decode()
	return ""
