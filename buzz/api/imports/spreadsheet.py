import csv
import io

import frappe
from frappe.utils import cstr
from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

from buzz.api.imports.exceptions import EmptySpreadsheet, TooManyRows, UnreadableFile

MAX_ROWS = 5000


class Spreadsheet:
	"""The header and the rows of an uploaded file or of cells pasted from a spreadsheet, as text."""

	def __init__(self, rows: list[list]):
		rows = [[cstr(cell).strip() for cell in row] for row in rows]
		rows = [row for row in rows if any(row)]
		if len(rows) < 2:
			EmptySpreadsheet.throw()
		if len(rows) - 1 > MAX_ROWS:
			TooManyRows.throw(limit=MAX_ROWS)
		self.header = rows[0]
		width = len(self.header)
		self.rows = [(row + [""] * width)[:width] for row in rows[1:]]

	@classmethod
	def load(cls, file_url: str | None, text: str | None) -> "Spreadsheet":
		if text:
			return cls(read_text(text))
		file = frappe.get_doc("File", {"file_url": file_url})
		file.check_permission("read")
		try:
			content = file.get_content()
			if file.file_name.lower().endswith(".xlsx"):
				return cls(read_xlsx_file_from_attached_file(fcontent=content))
			return cls(read_text(content.decode("utf-8-sig") if isinstance(content, bytes) else content))
		except (UnicodeDecodeError, ValueError, KeyError, OSError):
			UnreadableFile.throw()


def read_text(text: str) -> list[list[str]]:
	# Cells copied out of Google Sheets or Excel arrive tab-separated.
	first_line = text.split("\n", 1)[0]
	delimiter = "\t" if "\t" in first_line else ";" if first_line.count(";") > first_line.count(",") else ","
	return list(csv.reader(io.StringIO(text), delimiter=delimiter))
