import re

import frappe

DOCTYPES = ["Talk Proposal", "Sponsorship Enquiry"]


def execute():
	# Rewrite space-separated phone values ("+91 9000090000") to the hyphen format
	# ("+91-9000090000") that Frappe's Phone control needs to render them.
	# Each row is healed independently so one bad value can't abort the migration.
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

			# Never write a value that invents or reorders digits: the code must be a
			# prefix and the number a suffix of the original digits. (A doubled value
			# drops its duplicate code, so digit counts can legitimately differ.)
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

	# Heal only when a separator (space or hyphen) delimits the leading dial code(s)
	# from the number, e.g. "+91 9000090000" or "+91 +91 9000090000". A no-separator
	# value like "+919000090000" is ambiguous without a dial-code table, so it is left
	# untouched rather than mis-split into a wrong code and a truncated number.
	match = re.fullmatch(r"(?:\+\d{1,4}[\s-]+)+(\d+)", raw)
	if not match:
		return None

	code = re.match(r"\+\d{1,4}", raw).group(0)
	return f"{code}-{match.group(1)}"
