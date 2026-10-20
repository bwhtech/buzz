import difflib
import re
from dataclasses import dataclass
from functools import cached_property
from typing import ClassVar

import frappe
from frappe import _
from frappe.utils import strip_html

from buzz.api.events.exceptions import EventNotFound
from buzz.api.exceptions import NotPermitted
from buzz.api.imports.exceptions import ImportNotReady, ImportsNotEnabled, UnknownImportType
from buzz.api.imports.schemas import ImportCheck, ImportColumn, ImportIssue, ImportOption, ImportRowError
from buzz.api.imports.spreadsheet import Spreadsheet
from buzz.events.doctype.buzz_team_settings.buzz_team_settings import is_feature_enabled
from buzz.permissions import has_section_permission

IMPORT_FLAG = "feature_data_import"
CREATE = "__create__"
BLANK = "__blank__"
SKIP = "skip"
PROGRESS_EVENT = "buzz_import_progress"
DONE_EVENT = "buzz_import_done"


@dataclass(frozen=True)
class Field:
	label: str
	required: bool = False
	aliases: tuple[str, ...] = ()


def normalize(text: str) -> str:
	return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


class Importer:
	"""Reads a sheet into records, reports what blocks them, and imports the ones that can go in.

	`choices` is what the user picked on the check step: columns (header -> field, "" to leave
	out), values (field -> raw value -> option, CREATE or BLANK), skip_invalid, and for
	check-ins a date.
	"""

	section: str
	noun: str
	fields: ClassVar[dict[str, Field]]
	# Fields whose values must be one of the event's records -> whether a new one can be made.
	value_fields: ClassVar[dict[str, bool]] = {}
	# Imports create no mail of their own; this only decides the welcome email of a new user.
	send_emails = False

	def __init__(self, event: str, sheet: Spreadsheet, choices: dict):
		self.event = event
		self.sheet = sheet
		self.choices = choices
		self.created_values: dict[tuple[str, str], str] = {}
		self.run_notes: list[str] = []

	@property
	def event_doc(self):
		return frappe.get_cached_doc("Buzz Event", self.event)

	def ensure_permitted(self) -> None:
		if not has_section_permission(self.event, self.section, "write"):
			NotPermitted.throw()

	# Columns

	@cached_property
	def mapping(self) -> list[str | None]:
		chosen = self.choices.get("columns") or {}
		used: set[str] = set()
		mapping = []
		for header in self.sheet.header:
			field = (chosen[header] or None) if header in chosen else self.match(header, used)
			used.add(field)
			mapping.append(field)
		return mapping

	def match(self, header: str, used: set) -> str | None:
		name = normalize(header)
		for field, spec in self.fields.items():
			if field not in used and name in (field, normalize(spec.label), *spec.aliases):
				return field
		return None

	def suggestion(self, header: str) -> ImportOption | None:
		taken = set(self.mapping)
		names = {
			alias: field
			for field, spec in self.fields.items()
			if field not in taken
			for alias in (field, normalize(spec.label), *spec.aliases)
		}
		close = difflib.get_close_matches(normalize(header), names, n=1, cutoff=0.6)
		return self.field_option(names[close[0]]) if close else None

	def field_option(self, field: str) -> ImportOption:
		return ImportOption(value=field, label=self.fields[field].label)

	def missing_fields(self) -> list[str]:
		return [
			spec.label for field, spec in self.fields.items() if spec.required and field not in self.mapping
		]

	# Records

	@cached_property
	def records(self) -> list[dict]:
		records = []
		for index, row in enumerate(self.sheet.rows):
			record = {field: value for field, value in zip(self.mapping, row, strict=True) if field}
			record["row"] = index + 2
			records.append(record)
		return records

	def row_error(self, record: dict) -> str | None:
		for field, spec in self.fields.items():
			if spec.required and field in self.mapping and not record.get(field):
				return _("{0} is empty.").format(spec.label)
		return None

	def duplicate_keys(self, record: dict) -> list[str]:
		return []

	def existing_keys(self) -> set[str]:
		return set()

	@cached_property
	def sorted_records(self) -> tuple[list[dict], list[dict], list[dict]]:
		"""(ready, invalid, duplicate). A row repeating an earlier one in the file is a duplicate too."""
		ready, invalid, duplicate = [], [], []
		seen = self.existing_keys()
		for record in self.records:
			if error := self.row_error(record):
				invalid.append({**record, "error": error})
				continue
			keys = self.duplicate_keys(record)
			if keys and seen.issuperset(keys):
				duplicate.append(record)
				continue
			seen.update(keys)
			ready.append(record)
		return ready, invalid, duplicate

	# Values

	def options(self, field: str) -> list[ImportOption]:
		return []

	@cached_property
	def option_lookup(self) -> dict[str, dict[str, str]]:
		return {
			field: {
				key.lower(): option.value
				for option in self.options(field)
				for key in (option.value, option.label)
			}
			for field in self.value_fields
		}

	def chosen_value(self, field: str, raw: str) -> str | None:
		return (self.choices.get("values") or {}).get(field, {}).get(raw)

	def resolve(self, field: str, raw: str) -> str | None:
		"""The record a raw value stands for, creating it when the user asked to."""
		if not raw:
			return None
		if match := self.option_lookup[field].get(raw.lower()):
			return match
		choice = self.chosen_value(field, raw)
		if choice == CREATE:
			key = (field, raw)
			if key not in self.created_values:
				self.created_values[key] = self.create_value(field, raw)
			return self.created_values[key]
		return None if choice in (None, BLANK) else choice

	def create_value(self, field: str, raw: str) -> str:
		raise NotImplementedError

	def value_issues(self) -> list[ImportIssue]:
		issues = []
		for field, can_create in self.value_fields.items():
			if field not in self.mapping:
				continue
			counts: dict[str, int] = {}
			for record in self.records:
				raw = record.get(field)
				if raw and raw.lower() not in self.option_lookup[field]:
					counts[raw] = counts.get(raw, 0) + 1
			issues += [self.value_issue(field, raw, count, can_create) for raw, count in counts.items()]
		return issues

	def value_issue(self, field: str, raw: str, count: int, can_create: bool) -> ImportIssue:
		spec = self.fields[field]
		extra = [ImportOption(value=CREATE, label=_("Create {0}").format(raw))] if can_create else []
		if not spec.required:
			extra.append(ImportOption(value=BLANK, label=_("Leave empty")))
		return ImportIssue(
			kind="value",
			field=field,
			label=spec.label,
			value=raw,
			count=count,
			choice=self.chosen_value(field, raw),
			options=extra + self.options(field),
		)

	# Check

	def notes(self) -> list[str]:
		duplicates = len(self.sorted_records[2])
		if not duplicates:
			return []
		return [_("Already in this event, so left out: {0}.").format(duplicates)]

	def issues(self) -> list[ImportIssue]:
		issues = [
			ImportIssue(kind="column", column=header, suggestion=self.suggestion(header))
			for header, field in zip(self.sheet.header, self.mapping, strict=True)
			if not field and header not in (self.choices.get("columns") or {})
		]
		issues += [ImportIssue(kind="missing", label=label) for label in self.missing_fields()]
		issues += self.value_issues()
		invalid = self.sorted_records[1]
		if invalid:
			rows = [ImportRowError(row=record["row"], reason=record["error"]) for record in invalid]
			issues.append(
				ImportIssue(
					kind="rows",
					count=len(rows),
					rows=rows[:50],
					choice=SKIP if self.choices.get("skip_invalid") else None,
				)
			)
		return issues

	def check(self) -> ImportCheck:
		issues = self.issues()
		return ImportCheck(
			total_rows=len(self.records),
			ready_rows=len(self.sorted_records[0]),
			ready=all(issue.kind != "missing" and issue.choice for issue in issues),
			fields=[self.field_option(field) for field in self.fields],
			columns=[
				ImportColumn(column=header, field=field)
				for header, field in zip(self.sheet.header, self.mapping, strict=True)
			],
			issues=issues,
			notes=self.notes(),
		)

	# Run

	def import_record(self, record: dict) -> None:
		raise NotImplementedError

	def finish(self) -> None:
		"""After every row, for work done once per import."""

	def run(self) -> dict:
		ready = self.sorted_records[0]
		failed = []
		for done, record in enumerate(ready, 1):
			frappe.db.savepoint("import_row")
			try:
				self.import_record(record)
			except Exception as error:
				# One bad row fails alone; the reason goes back to the user with the row.
				frappe.db.rollback(save_point="import_row")
				failed.append({"row": record["row"], "reason": failure_reason(error)})
			frappe.clear_messages()
			if done % 25 == 0 or done == len(ready):
				self.publish(PROGRESS_EVENT, done=done, total=len(ready))
		self.finish()
		return {"imported": len(ready) - len(failed), "failed": failed, "notes": self.run_notes}

	def publish(self, event: str, **message) -> None:
		message.update(event=self.event, import_type=self.noun)
		frappe.publish_realtime(event, message, user=frappe.session.user)


def failure_reason(error: Exception) -> str:
	# frappe.throw leaves its text in the message log; a bare PermissionError carries none.
	messages = [entry.get("message") for entry in frappe.local.message_log if isinstance(entry, dict)]
	return strip_html(str(error) or (messages[-1] if messages else "")) or _("Could not import.")


def build_importer(
	event: str, import_type: str, file_url: str | None, text: str | None, choices: dict
) -> Importer:
	from buzz.api.imports.checkins import CheckInImporter
	from buzz.api.imports.sponsors import SponsorImporter
	from buzz.api.imports.talks import TalkImporter

	importers = {"checkins": CheckInImporter, "talks": TalkImporter, "sponsors": SponsorImporter}
	if import_type not in importers:
		UnknownImportType.throw(import_type=import_type)
	ensure_imports_enabled(event)
	importer = importers[import_type](event, Spreadsheet.load(file_url, text), choices)
	importer.ensure_permitted()
	return importer


def start(importer: Importer, send_emails: bool, source: dict) -> None:
	if not importer.check().ready:
		ImportNotReady.throw()
	frappe.enqueue(
		run_import,
		queue="long",
		timeout=3600,
		now=frappe.flags.in_test,
		enqueue_after_commit=True,
		send_emails=send_emails,
		# One dict: `event` is a keyword enqueue keeps for itself.
		source=source,
	)


def run_import(send_emails: bool, source: dict) -> None:
	importer = build_importer(**source)
	importer.send_emails = send_emails
	try:
		result = importer.run()
	except Exception:
		# The card on the page waits for an answer either way.
		importer.publish(DONE_EVENT, error=_("The import failed and nothing was saved. Try again."))
		raise
	failed_rows = {item["row"] for item in result["failed"]}
	importer.publish(
		DONE_EVENT,
		**result,
		header=importer.sheet.header,
		failed_cells=[row for index, row in enumerate(importer.sheet.rows) if index + 2 in failed_rows],
	)


def ensure_imports_enabled(event: str) -> None:
	team = frappe.db.get_value("Buzz Event", event, "team")
	if team is None and not frappe.db.exists("Buzz Event", event):
		EventNotFound.throw()
	if not team or not is_feature_enabled(team, IMPORT_FLAG):
		ImportsNotEnabled.throw()
