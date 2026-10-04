from typing import Literal

from buzz.api.schemas import APIResponse


class FilterOption(APIResponse):
	value: str
	label: str


class FilterOperator(APIResponse):
	operator: str
	label: str
	# Set when choosing the operator also fixes the value, as "is answered" fixes "set".
	value: str | None = None


class FilterField(APIResponse):
	"""One field a list can be filtered on, with the operators it allows."""

	key: str
	label: str
	fieldtype: str
	section: Literal["standard", "question"]
	options: list[FilterOption]
	operators: list[FilterOperator]
