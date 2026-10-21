import frappe
from frappe import _
from frappe.utils import strip_html

from buzz.api.events.exceptions import EventNotFound
from buzz.api.imports.exceptions import ImportNotReady, ImportRunning, ImportsNotEnabled
from buzz.api.imports.schemas import ImportStatus
from buzz.api.imports.sponsors import SponsorImporter
from buzz.api.imports.spreadsheet import Spreadsheet
from buzz.events.doctype.buzz_team_settings.buzz_team_settings import IMPORT_FLAG, is_feature_enabled

# A finished import's result stays readable this long, for a page that polls late.
STATUS_TTL = 3600


def build_importer(event: str, file_url: str | None, text: str | None, choices: dict) -> SponsorImporter:
	ensure_imports_enabled(event)
	importer = SponsorImporter(event, Spreadsheet.load(file_url, text), choices)
	importer.ensure_permitted()
	return importer


def start(importer: SponsorImporter, source: dict) -> None:
	status = import_status(importer.event)
	if status and status.state != "done":
		ImportRunning.throw()
	check = importer.check()
	if not check.ready:
		ImportNotReady.throw()
	save_status(importer.event, state="queued", total=check.ready_rows)
	frappe.enqueue(
		run_import,
		queue="long",
		timeout=3600,
		now=frappe.flags.in_test,
		enqueue_after_commit=True,
		# One dict: `event` is a keyword enqueue keeps for itself.
		source=source,
	)


def run_import(source: dict) -> None:
	try:
		importer = build_importer(**source)
		result = import_rows(importer)
	except Exception:
		# The page polls until it reads a finished status, so it gets one either way.
		error = _("The import failed and nothing was saved. Try again.")
		save_status(source["event"], state="done", error=error)
		raise
	failed_rows = {item["row"] for item in result["failed"]}
	sheet = importer.sheet
	save_status(
		importer.event,
		state="done",
		**result,
		header=sheet.header,
		failed_cells=[
			row for number, row in zip(sheet.row_numbers, sheet.rows, strict=True) if number in failed_rows
		],
	)


def import_rows(importer: SponsorImporter) -> dict:
	ready = importer.sorted_records[0]
	failed = []
	for done, record in enumerate(ready, 1):
		frappe.db.savepoint("import_row")
		try:
			importer.import_record(record)
		except Exception as error:
			# One bad row fails alone; the reason goes back to the user with the row.
			frappe.db.rollback(save_point="import_row")
			failed.append(importer.row_error_item(record, failure_reason(error)).model_dump())
		frappe.clear_messages()
		# About fifty writes per import: enough for the bar, cheap for the cache.
		if done % max(1, len(ready) // 50) == 0 or done == len(ready):
			save_status(importer.event, state="running", done=done, total=len(ready))
	return {"imported": len(ready) - len(failed), "failed": failed}


def failure_reason(error: Exception) -> str:
	# frappe.throw leaves its text in the message log; a bare PermissionError carries none.
	messages = [entry.get("message") for entry in frappe.local.message_log if isinstance(entry, dict)]
	return strip_html(str(error) or (messages[-1] if messages else "")) or _("Could not import.")


def ensure_imports_enabled(event: str) -> None:
	team = frappe.db.get_value("Buzz Event", event, "team")
	if team is None and not frappe.db.exists("Buzz Event", event):
		EventNotFound.throw()
	if not team or not is_feature_enabled(team, IMPORT_FLAG):
		ImportsNotEnabled.throw()


# Keyed by user: an import's status is only ever read by the person who started it.
def status_key(event: str) -> str:
	return f"buzz_sponsor_import_status:{frappe.session.user}:{event}"


def save_status(event: str, **status) -> None:
	frappe.cache.set_value(status_key(event), status, expires_in_sec=STATUS_TTL)


def import_status(event: str) -> ImportStatus | None:
	status = frappe.cache.get_value(status_key(event))
	return ImportStatus(**status) if status else None
