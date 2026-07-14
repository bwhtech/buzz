import re

import frappe

DOCTYPES = ["Talk Proposal", "Sponsorship Enquiry"]


def execute():
	# Normalize legacy dashboard phone values ("+91 9000090000" / doubled
	# "+91 +91 ...") to Frappe's canonical "+91-9000090000" so Desk can render them.
	for doctype in DOCTYPES:
		rows = frappe.get_all(doctype, filters={"phone": ["is", "set"]}, fields=["name", "phone"])
		for row in rows:
			normalized = _normalize(row.phone)
			if normalized and normalized != row.phone:
				frappe.db.set_value(doctype, row.name, "phone", normalized, update_modified=False)


def _normalize(value: str) -> str | None:
	raw = (value or "").strip()
	if not raw or "-" in raw:
		return None
	prefix = re.match(r"^(?:\s*\+\d{1,4}[\s-]*)+", raw)
	if not prefix:
		return None
	code = re.match(r"^\s*(\+\d{1,4})", raw).group(1)
	digits = re.sub(r"\D", "", raw[prefix.end() :])
	if not digits:
		return None
	return f"{code}-{digits}"
