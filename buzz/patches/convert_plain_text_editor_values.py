import re

import frappe
from frappe.utils import escape_html

HTML_TAG = re.compile(r"<[a-z][\s\S]*>", re.IGNORECASE)
BLANK_LINES = re.compile(r"\n\s*\n")

TEXT_EDITOR_FIELDS = {
	"Talk Proposal": "description",
	"Event Talk": "description",
	"Event Proposal": "about",
}


def plain_text_to_html(value: str) -> str:
	"""Blank lines separate paragraphs and single line breaks become <br>."""
	paragraphs = BLANK_LINES.split(escape_html(value.replace("\r\n", "\n").strip()))
	return "".join(f"<p>{'<br>'.join(paragraph.splitlines())}</p>" for paragraph in paragraphs)


def needs_conversion(value: str | None) -> bool:
	return bool(value and value.strip() and not HTML_TAG.search(value))


def execute():
	for doctype, fieldname in TEXT_EDITOR_FIELDS.items():
		for row in frappe.get_all(doctype, fields=["name", fieldname]):
			if needs_conversion(row[fieldname]):
				frappe.db.set_value(
					doctype,
					row.name,
					fieldname,
					plain_text_to_html(row[fieldname]),
					update_modified=False,
				)
