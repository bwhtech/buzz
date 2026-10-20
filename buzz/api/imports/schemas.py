from typing import Literal

from pydantic import Field

from buzz.api.schemas import APIResponse


class ImportOption(APIResponse):
	value: str
	label: str


class ImportColumn(APIResponse):
	column: str
	field: str | None


class ImportRowError(APIResponse):
	row: int
	reason: str


class ImportIssue(APIResponse):
	"""Something to sort out before importing. `choice` is what the user picked, None while open.

	column: a column nothing matched. missing: a required field no column fills.
	value: a value the event does not have. rows: rows that cannot be imported as they are.
	"""

	kind: Literal["column", "missing", "value", "rows"]
	choice: str | None = None
	column: str | None = None
	suggestion: ImportOption | None = None
	field: str | None = None
	label: str | None = None
	value: str | None = None
	count: int = 0
	options: list[ImportOption] = Field(default_factory=list)
	rows: list[ImportRowError] = Field(default_factory=list)


class ImportCheck(APIResponse):
	total_rows: int
	ready_rows: int
	ready: bool
	fields: list[ImportOption]
	columns: list[ImportColumn]
	issues: list[ImportIssue]
	notes: list[str]
	# Check-ins only: the event's days, offered when the file has no date column.
	days: list[ImportOption] = Field(default_factory=list)
