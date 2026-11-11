import csv
import io
from zipfile import BadZipFile, ZipFile

import frappe
from frappe.utils import cstr
from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file
from openpyxl.utils.exceptions import InvalidFileException

from buzz.api.imports.exceptions import EmptySpreadsheet, TooManyRows, UnreadableFile

MAX_ROWS = 5000
MAX_FILE_BYTES = 5 * 1024 * 1024
# A small zip can expand far past MAX_FILE_BYTES once every member is unpacked.
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024


class Spreadsheet:
	"""The header and the rows of an uploaded file or of cells pasted from a spreadsheet, as text."""

	def __init__(self, rows: list[list]):
		cells = [[cstr(cell).strip() for cell in row] for row in rows]
		numbered = [(number, row) for number, row in enumerate(cells, 1) if any(row)]
		if len(numbered) < 2:
			EmptySpreadsheet.throw()
		if len(numbered) - 1 > MAX_ROWS:
			TooManyRows.throw(limit=MAX_ROWS)
		self.header = numbered[0][1]
		width = len(self.header)
		# Each row's number in the file, blank rows counted, so errors point where the user looks.
		self.row_numbers = [number for number, _row in numbered[1:]]
		self.rows = [(row + [""] * width)[:width] for _number, row in numbered[1:]]

	@classmethod
	def load(cls, file_url: str | None, text: str | None) -> "Spreadsheet":
		if text:
			return cls(read_text(text))
		if not file_url:
			EmptySpreadsheet.throw()
		file = frappe.get_doc("File", {"file_url": file_url})
		file.check_permission("read")
		ensure_file_size(file)
		try:
			content = file.get_content()
			if file.file_name.lower().endswith(".xlsx"):
				# get_content hands back text when the bytes decode, as a CSV renamed to .xlsx does.
				workbook = content.encode() if isinstance(content, str) else content
				ensure_uncompressed_size(workbook)
				return cls(read_xlsx_file_from_attached_file(fcontent=workbook))
			return cls(read_text(content.decode("utf-8-sig") if isinstance(content, bytes) else content))
		except (UnicodeDecodeError, ValueError, KeyError, OSError, BadZipFile, InvalidFileException):
			UnreadableFile.throw()


def ensure_file_size(file) -> None:
	if not file.file_size or file.file_size > MAX_FILE_BYTES:
		UnreadableFile.throw()


def ensure_uncompressed_size(workbook: bytes) -> None:
	# Reading the central directory is cheap; parsing every member is not.
	with ZipFile(io.BytesIO(workbook)) as archive:
		expanded = sum(member.file_size for member in archive.infolist())
	if expanded > MAX_UNCOMPRESSED_BYTES:
		UnreadableFile.throw()


def read_text(text: str) -> list[list[str]]:
	# Cells copied out of Google Sheets or Excel arrive tab-separated.
	first_line = text.split("\n", 1)[0]
	delimiter = "\t" if "\t" in first_line else ";" if first_line.count(";") > first_line.count(",") else ","
	return list(csv.reader(io.StringIO(text), delimiter=delimiter))
