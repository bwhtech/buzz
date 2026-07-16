import re

import frappe

DOCTYPES = ["Talk Proposal", "Sponsorship Enquiry"]


def execute():
	# Normalize legacy dashboard phone values ("+91 9000090000" / doubled
	# "+91 +91 ...") to Frappe's canonical "+91-9000090000" so Desk can render them.
	# Each row is healed independently: a single bad value is logged and skipped
	# so it can never abort the whole migration.
	for doctype in DOCTYPES:
		rows = frappe.get_all(doctype, filters={"phone": ["is", "set"]}, fields=["name", "phone"])
		for row in rows:
			try:
				normalized = _normalize(row.phone)
			except Exception:
				frappe.log_error(
					title="normalize_phone_format: parse failed",
					message=f"{doctype} {row.name} phone={row.phone!r}\n{frappe.get_traceback()}",
				)
				continue

			if not normalized or normalized == row.phone:
				continue

			# Guard against corruption: the code must be a prefix and the number a
			# suffix of the original digits (nothing invented or reordered). A doubled
			# value legitimately drops the duplicated code, so we cannot require equal
			# digit counts — only that no new digits appear and the number is intact.
			raw_digits = re.sub(r"\D", "", row.phone)
			code_part, _, number_part = normalized.partition("-")
			code_digits = re.sub(r"\D", "", code_part)
			if not (raw_digits.startswith(code_digits) and raw_digits.endswith(number_part)):
				frappe.log_error(
					title="normalize_phone_format: digit mismatch, skipped",
					message=f"{doctype} {row.name} {row.phone!r} -> {normalized!r}",
				)
				continue

			try:
				frappe.db.set_value(doctype, row.name, "phone", normalized, update_modified=False)
			except Exception:
				frappe.log_error(
					title="normalize_phone_format: update failed",
					message=f"{doctype} {row.name} {row.phone!r} -> {normalized!r}\n{frappe.get_traceback()}",
				)


def _normalize(value: str) -> str | None:
	raw = (value or "").strip()
	if not raw:
		return None

	# Already canonical "<code>-<digits>": nothing to do (keeps the patch idempotent).
	if re.fullmatch(r"\+\d{1,4}-\d+", raw):
		return None

	# Only heal values where one or more leading dial codes are separated from the
	# number by whitespace or a hyphen: "+91 9000090000", "+91 +91 9000090000",
	# "+91 +91-9000090000". Requiring an explicit separator means an ambiguous
	# no-separator value like "+919000090000" is left untouched rather than
	# mis-split (e.g. into "+9190-..."), which would corrupt the number.
	match = re.fullmatch(r"(?:\+\d{1,4}[\s-]+)+(\d+)", raw)
	if not match:
		return None

	code = re.match(r"\+\d{1,4}", raw).group(0)
	return f"{code}-{match.group(1)}"
