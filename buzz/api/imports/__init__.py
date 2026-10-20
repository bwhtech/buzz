import frappe

from buzz.api.imports import services
from buzz.api.imports.schemas import ImportCheck


@frappe.whitelist(methods=["POST"])
def check_import(
	event: str,
	import_type: str,
	file_url: str | None = None,
	text: str | None = None,
	choices: dict | str | None = None,
) -> ImportCheck:
	"""What a file would import, and what has to be sorted out first. POST: pasted rows ride in the body."""
	return services.build_importer(
		event, import_type, file_url, text, frappe.parse_json(choices or {})
	).check()


@frappe.whitelist(methods=["POST"])
def start_import(
	event: str,
	import_type: str,
	file_url: str | None = None,
	text: str | None = None,
	choices: dict | str | None = None,
	send_emails: bool = False,
) -> None:
	"""Imports in the background, reporting progress and the result over the socket."""
	choices = frappe.parse_json(choices or {})
	source = {
		"event": event,
		"import_type": import_type,
		"file_url": file_url,
		"text": text,
		"choices": choices,
	}
	services.start(services.build_importer(**source), send_emails, source)
