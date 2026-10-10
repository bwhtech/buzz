import frappe
from frappe import _
from frappe.utils import cstr, flt

from buzz.api.filters.exceptions import InvalidFilter
from buzz.api.filters.schemas import FilterField, FilterOperator, FilterOption

KIND_BY_FIELDTYPE = {
	"Select": "choice",
	"Link": "choice",
	"Check": "choice",
	"Multi Select": "multi",
	"Number": "number",
	"Rating": "number",
	"Date": "date",
	"Attach": "file",
	"Attach Image": "file",
}
# A record's Buzz Tags, matched through its Buzz Tag Link rows.
TAGS_KEY = "tags"

NEGATED_OPERATORS = {"not in": "in", "not like": "like"}
# Answers saved through `str()` carry Python's spelling: "True" for a tick, ['a', 'b'] for a list.
CHECKED_VALUES = ["1", "True", "true"]


def kind_of(fieldtype: str) -> str:
	return KIND_BY_FIELDTYPE.get(fieldtype, "text")


def operators_of(kind: str) -> list[tuple[str, str]]:
	"""Frappe's own filter operators, labelled the way a list reads them."""
	return {
		"choice": [("in", _("is")), ("not in", _("is not"))],
		"multi": [("like", _("includes")), ("not like", _("excludes"))],
		"text": [("like", _("contains")), ("not like", _("does not contain")), ("=", _("is exactly"))],
		"number": [
			("=", _("is")),
			(">", _("is more than")),
			("<", _("is less than")),
			("between", _("is between")),
		],
		"date": [
			("=", _("is on")),
			("<", _("is before")),
			(">", _("is after")),
			("between", _("is between")),
		],
		"file": [],
	}[kind]


def filter_field(key, label, fieldtype, options=(), section="standard") -> FilterField:
	operators = [FilterOperator(operator=op, label=text) for op, text in operators_of(kind_of(fieldtype))]
	if section == "question":
		operators += [
			FilterOperator(operator="is", value="set", label=_("is answered")),
			FilterOperator(operator="is", value="not set", label=_("is not answered")),
		]
	return FilterField(
		key=key,
		label=label,
		fieldtype=fieldtype,
		section=section,
		options=[FilterOption(value=value, label=text) for value, text in options],
		operators=operators,
	)


def tags_field(tags) -> FilterField:
	return filter_field(TAGS_KEY, _("Tags"), "Link", [(tag.name, tag.label) for tag in tags])


def question_fields(questions) -> list[FilterField]:
	"""Buzz Form Field rows as filters; answers are matched in Additional Field by fieldname."""
	return [
		filter_field(row.fieldname, row.label, row.fieldtype, question_options(row), "question")
		for row in questions
	]


def event_questions(event: str, **filters) -> list:
	"""An event's enabled Buzz Custom Field questions, in form order."""
	return frappe.get_all(
		"Buzz Custom Field",
		filters={"event": event, "enabled": 1, **filters},
		fields=["fieldname", "label", "fieldtype", "options", "applied_to"],
		order_by="order asc",
	)


def question_options(row) -> list[tuple[str, str]]:
	if row.fieldtype == "Check":
		return [("1", _("Yes")), ("0", _("No"))]
	if row.fieldtype in ("Select", "Multi Select"):
		return [(option, option) for option in (row.options or "").splitlines() if option.strip()]
	return []


def is_blank(operator: str, value) -> bool:
	"""A chip still being filled in narrows nothing; `between` waits for both ends."""
	values = [cstr(item).strip() for item in (value if isinstance(value, list) else [value])]
	return not all(values) if operator == "between" else not any(values)


class ListConditions:
	"""Turns the dashboard's `[field, operator, value]` triples into `frappe.get_all` filters."""

	def __init__(self, doctype: str, fields: list[FilterField], answer_parents: dict | None = None):
		"""`answer_parents` maps a question answered on a linked record to that record's doctype
		and the list field linking to it, as a guest's booking questions sit on the booking."""
		self.doctype = doctype
		self.fields = {field.key: field for field in fields}
		self.answer_parents = answer_parents or {}

	def frappe_filters(self, filters_json: str | None) -> list[list]:
		translated = (self.translate(*triple) for triple in self.parse(filters_json))
		return [condition for condition in translated if condition]

	def parse(self, filters_json: str | None) -> list[list]:
		triples = frappe.parse_json(filters_json) if filters_json else []
		if not isinstance(triples, list) or any(not self.is_valid(triple) for triple in triples):
			InvalidFilter.throw()
		return triples

	def is_valid(self, triple) -> bool:
		if not isinstance(triple, list) or len(triple) != 3 or not isinstance(triple[0], str):
			return False
		field = self.fields.get(triple[0])
		return bool(field) and any(choice.operator == triple[1] for choice in field.operators)

	def translate(self, key: str, operator: str, value) -> list | None:
		if is_blank(operator, value):
			return None
		if key == TAGS_KEY:
			return ["name", operator, self.tagged_names(value)]
		field = self.fields[key]
		if field.section == "question":
			doctype, link_field = self.answer_parents.get(key, (self.doctype, "name"))
			return AnswerCondition(doctype, link_field, field, operator, value).name_filter()
		return [key, operator, f"%{value}%" if "like" in operator else value]

	def tagged_names(self, tags: list[str]) -> list[str]:
		return frappe.get_all(
			"Buzz Tag Link",
			filters={"document_type": self.doctype, "tag": ["in", tags]},
			pluck="document_name",
		)


class AnswerCondition:
	"""One condition on a custom question, resolved to the parents whose answer matches.

	The answers live in Additional Field rows, and frappe joins a child table only once, so
	each question is looked up on its own and lands back on the list as `name in (...)`.
	"""

	# Name lists grow with how many records answered the question; move to a qb
	# subquery if a list ever reaches tens of thousands of rows.

	def __init__(self, doctype: str, link_field: str, field: FilterField, operator: str, value):
		self.doctype = doctype
		self.link_field = link_field
		self.field = field
		self.operator = operator
		self.values = value if isinstance(value, list) else [value]

	def name_filter(self) -> list | None:
		if self.operator == "is":
			return [self.link_field, "in" if self.values[0] == "set" else "not in", self.answered_parents()]
		if self.field.fieldtype == "Check":
			return self.check_filter()
		# Negations take the complement, so an unanswered question counts as not matching.
		positive_operator = NEGATED_OPERATORS.get(self.operator, self.operator)
		return [
			self.link_field,
			"not in" if self.operator in NEGATED_OPERATORS else "in",
			self.matching_parents(positive_operator),
		]

	def check_filter(self) -> list | None:
		"""A Check left unticked may have no row at all, so "No" means "not Yes"."""
		selected_values = set(self.values)
		if self.operator == "not in":
			selected_values = {"0", "1"} - selected_values
		if len(selected_values) != 1:
			return None
		return [
			self.link_field,
			"in" if selected_values == {"1"} else "not in",
			self.answered_parents(["in", CHECKED_VALUES]),
		]

	def matching_parents(self, operator: str) -> list[str]:
		kind = kind_of(self.field.fieldtype)
		if kind in ("number", "date"):
			return self.compared_parents(operator)
		if kind == "multi":
			# A Multi Select answer is a list in text, so each option sits quoted inside it.
			patterns = [f'%"{option}"%' for option in self.values] + [
				f"%'{option}'%" for option in self.values
			]
			return list({name for pattern in patterns for name in self.answered_parents(["like", pattern])})
		if operator == "like":
			return self.answered_parents(["like", f"%{self.values[0]}%"])
		return self.answered_parents([operator, self.values if operator == "in" else self.values[0]])

	def compared_parents(self, operator: str) -> list[str]:
		"""Answers are text, so numbers and dates are compared here rather than in SQL."""
		convert = flt if kind_of(self.field.fieldtype) == "number" else str
		low, high = convert(self.values[0]), convert(self.values[-1])
		matches = {
			"=": lambda answer: answer == low,
			">": lambda answer: answer > low,
			"<": lambda answer: answer < low,
			"between": lambda answer: low <= answer <= high,
		}[operator]
		rows = frappe.get_all("Additional Field", filters=self.answer_filters(), fields=["parent", "value"])
		return [row.parent for row in rows if row.value not in (None, "") and matches(convert(row.value))]

	def answered_parents(self, value=None) -> list[str]:
		filters = self.answer_filters()
		filters["value"] = value if value is not None else ["is", "set"]
		return frappe.get_all("Additional Field", filters=filters, pluck="parent")

	def answer_filters(self) -> dict:
		return {"parenttype": self.doctype, "parentfield": "additional_fields", "fieldname": self.field.key}
