import difflib
import re
from dataclasses import dataclass
from functools import cached_property

import frappe
from frappe import _
from frappe.utils import validate_email_address

from buzz.api.exceptions import NotPermitted
from buzz.api.imports.schemas import (
	ImportCheck,
	ImportColumn,
	ImportIssue,
	ImportOption,
	ImportPreviewRow,
	ImportRowError,
)
from buzz.api.imports.spreadsheet import Spreadsheet
from buzz.permissions import has_section_permission

BLANK = "__blank__"
SKIP = "skip"
PREVIEW_LIMIT = 100


@dataclass(frozen=True)
class Field:
	label: str
	required: bool = False
	aliases: tuple[str, ...] = ()


FIELDS = {
	"company_name": Field(
		"Company Name", True, ("company", "name", "sponsor", "sponsor_name", "organisation")
	),
	"tier": Field("Tier", True, ("level", "sponsorship_tier", "package", "plan")),
	"website": Field("Website", aliases=("url", "site", "web")),
	"country": Field("Country"),
	"contact_email": Field("Contact Email", aliases=("email", "contact", "e_mail")),
	"company_logo": Field("Logo URL", aliases=("logo", "logo_link", "image")),
}
# Fields whose values must be one of the event's tiers or a country.
VALUE_FIELDS = ("tier", "country")


def normalize(text: str) -> str:
	return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


class SponsorImporter:
	"""Reads a sheet into sponsors on the event's tiers, reports what blocks them, and imports the rest.

	`choices` is what the user picked on the check step: columns (header -> field, "" to leave
	out), values (field -> raw value -> option or BLANK) and skip_invalid.
	"""

	def __init__(self, event: str, sheet: Spreadsheet, choices: dict):
		self.event = event
		self.sheet = sheet
		self.choices = choices

	def ensure_permitted(self) -> None:
		if not has_section_permission(self.event, "sponsors", "write"):
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
		for field, spec in FIELDS.items():
			if field not in used and name in (field, normalize(spec.label), *spec.aliases):
				return field
		return None

	def suggestion(self, header: str) -> ImportOption | None:
		taken = set(self.mapping)
		names = {
			alias: field
			for field, spec in FIELDS.items()
			if field not in taken
			for alias in (field, normalize(spec.label), *spec.aliases)
		}
		close = difflib.get_close_matches(normalize(header), names, n=1, cutoff=0.6)
		return self.field_option(names[close[0]]) if close else None

	def field_option(self, field: str) -> ImportOption:
		return ImportOption(value=field, label=FIELDS[field].label)

	def missing_fields(self) -> list[str]:
		return [spec.label for field, spec in FIELDS.items() if spec.required and field not in self.mapping]

	# Records

	@cached_property
	def records(self) -> list[dict]:
		records = []
		for number, row in zip(self.sheet.row_numbers, self.sheet.rows, strict=True):
			record = {field: value for field, value in zip(self.mapping, row, strict=True) if field}
			record["row"] = number
			records.append(record)
		return records

	def row_error(self, record: dict) -> str | None:
		for field, spec in FIELDS.items():
			if spec.required and field in self.mapping and not record.get(field):
				return _("{0} is empty.").format(spec.label)
		if error := self.length_error(record):
			return error
		email = record.get("contact_email")
		if email and not validate_email_address(email):
			return _("{0} isn't an email.").format(email)
		logo = record.get("company_logo")
		if logo and not logo.startswith(("http://", "https://", "/files/")):
			return _("The logo {0} isn't a link.").format(logo)
		return None

	def length_error(self, record: dict) -> str | None:
		meta = frappe.get_meta("Event Sponsor")
		for field in ("company_name", "website", "contact_email"):
			limit = meta.get_field(field).length or frappe.db.VARCHAR_LEN
			if len(record.get(field) or "") > limit:
				return _("{0} is longer than {1} characters.").format(FIELDS[field].label, limit)
		return None

	@cached_property
	def sorted_records(self) -> tuple[list[dict], list[dict], list[dict]]:
		"""(ready, invalid, duplicate). A name repeating an earlier row in the file is a duplicate too."""
		ready, invalid, duplicate = [], [], []
		names = frappe.get_all("Event Sponsor", filters={"event": self.event}, pluck="company_name")
		seen = {name.lower() for name in names}
		for record in self.records:
			if error := self.row_error(record):
				invalid.append({**record, "error": error})
				continue
			key = (record.get("company_name") or "").lower()
			if key in seen:
				duplicate.append(record)
				continue
			seen.add(key)
			ready.append(record)
		return ready, invalid, duplicate

	# Values

	@cached_property
	def tier_options(self) -> list[ImportOption]:
		tiers = frappe.get_all("Sponsorship Tier", filters={"event": self.event}, fields=["name", "title"])
		return [ImportOption(value=tier.name, label=tier.title) for tier in tiers]

	@cached_property
	def country_options(self) -> list[ImportOption]:
		return [ImportOption(value=name, label=name) for name in frappe.get_all("Country", pluck="name")]

	def options(self, field: str) -> list[ImportOption]:
		return self.tier_options if field == "tier" else self.country_options

	@cached_property
	def option_lookup(self) -> dict[str, dict[str, str]]:
		return {
			field: {
				key.lower(): option.value
				for option in self.options(field)
				for key in (option.value, option.label)
			}
			for field in VALUE_FIELDS
		}

	def chosen_value(self, field: str, raw: str) -> str | None:
		return (self.choices.get("values") or {}).get(field, {}).get(raw)

	def resolve(self, field: str, raw: str | None) -> str | None:
		"""The record a raw value stands for: a match by name or title, else the user's pick."""
		if not raw:
			return None
		value = self.option_lookup[field].get(raw.lower()) or self.chosen_value(field, raw)
		return None if value == BLANK else value

	def value_issues(self) -> list[ImportIssue]:
		issues = []
		for field in VALUE_FIELDS:
			if field not in self.mapping:
				continue
			counts: dict[str, int] = {}
			# Only rows that will import: a duplicate or a bad row needs no answer.
			for record in self.sorted_records[0]:
				raw = record.get(field)
				if raw and raw.lower() not in self.option_lookup[field]:
					counts[raw] = counts.get(raw, 0) + 1
			issues += [self.value_issue(field, raw, count) for raw, count in counts.items()]
		return issues

	def value_issue(self, field: str, raw: str, count: int) -> ImportIssue:
		spec = FIELDS[field]
		blank = [] if spec.required else [ImportOption(value=BLANK, label=_("Leave empty"))]
		return ImportIssue(
			kind="value",
			field=field,
			label=spec.label,
			value=raw,
			count=count,
			choice=self.chosen_value(field, raw),
			options=blank + self.options(field),
		)

	# Check

	def notes(self) -> list[str]:
		notes = []
		if duplicates := len(self.sorted_records[2]):
			notes.append(
				_("Already in this event or repeated in the file, so left out: {0}.").format(duplicates)
			)
		if without_logo := sum(1 for record in self.sorted_records[0] if not record.get("company_logo")):
			notes.append(
				_("Without a logo, so they show their name until one is added: {0}.").format(without_logo)
			)
		return notes

	def issues(self) -> list[ImportIssue]:
		issues = [
			ImportIssue(kind="column", column=header, suggestion=self.suggestion(header))
			for header, field in zip(self.sheet.header, self.mapping, strict=True)
			if not field and header not in (self.choices.get("columns") or {})
		]
		issues += [ImportIssue(kind="missing", label=label) for label in self.missing_fields()]
		issues += self.value_issues()
		if invalid := self.sorted_records[1]:
			rows = [self.row_error_item(record, record["error"]) for record in invalid]
			skip = SKIP if self.choices.get("skip_invalid") else None
			issues.append(ImportIssue(kind="rows", count=len(rows), rows=rows[:50], choice=skip))
		return issues

	def row_error_item(self, record: dict, reason: str) -> ImportRowError:
		return ImportRowError(row=record["row"], title=record.get("company_name"), reason=reason)

	@cached_property
	def tier_titles(self) -> dict[str, str]:
		return {option.value: option.label for option in self.tier_options}

	def preview(self, record: dict) -> dict[str, str | None]:
		"""A ready row as the user will see it once imported, values resolved to their labels."""
		return {
			**{field: record.get(field) for field in FIELDS},
			"website": website_url(record.get("website")),
			"tier": self.tier_titles.get(self.resolve("tier", record.get("tier"))),
			"country": self.resolve("country", record.get("country")),
		}

	def check(self) -> ImportCheck:
		issues = self.issues()
		ready = self.sorted_records[0]
		return ImportCheck(
			total_rows=len(self.records),
			ready_rows=len(ready),
			ready=all(issue.kind != "missing" and issue.choice for issue in issues),
			fields=[self.field_option(field) for field in FIELDS],
			columns=[
				ImportColumn(column=header, field=field)
				for header, field in zip(self.sheet.header, self.mapping, strict=True)
			],
			issues=issues,
			notes=self.notes(),
			preview=[
				ImportPreviewRow(row=record["row"], values=self.preview(record))
				for record in ready[:PREVIEW_LIMIT]
			],
		)

	# Run

	def import_record(self, record: dict) -> None:
		frappe.get_doc(
			{
				"doctype": "Event Sponsor",
				"event": self.event,
				"company_name": record["company_name"],
				"tier": self.resolve("tier", record["tier"]),
				"website": website_url(record.get("website")),
				"country": self.resolve("country", record.get("country")),
				"contact_email": record.get("contact_email"),
				"company_logo": record.get("company_logo"),
			}
		).insert()


def website_url(website: str | None) -> str | None:
	"""Sheets often hold a bare domain, which the URL field would reject."""
	return f"https://{website}" if website and "://" not in website else website
