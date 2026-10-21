import frappe

from buzz.api.imports import services
from buzz.api.imports.schemas import ImportCheck, ImportStatus


@frappe.whitelist(methods=["POST"])
def check_import(
	event: str,
	file_url: str | None = None,
	text: str | None = None,
	choices: dict | str | None = None,
) -> ImportCheck:
	"""What a sponsor file would import, and what has to be sorted out first. POST: pasted rows ride in the body."""
	return services.build_importer(event, file_url, text, frappe.parse_json(choices or {})).check()


@frappe.whitelist(methods=["POST"])
def start_import(
	event: str,
	file_url: str | None = None,
	text: str | None = None,
	choices: dict | str | None = None,
) -> None:
	"""Imports in the background. The page follows it with get_import_status."""
	source = {"event": event, "file_url": file_url, "text": text, "choices": frappe.parse_json(choices or {})}
	services.start(services.build_importer(**source), source)


@frappe.whitelist()
def get_import_status(event: str) -> ImportStatus | None:
	"""The session user's latest sponsor import on this event, polled while it runs."""
	return services.import_status(event)
