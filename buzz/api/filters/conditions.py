import frappe
from frappe import _
from frappe.query_builder.functions import Cast_
from frappe.utils import cstr, flt
from pypika.terms import Criterion, ExistsCriterion, ValueWrapper

from buzz.api.filters.exceptions import InvalidFilter
from buzz.api.filters.schemas import FilterField, FilterOperator, FilterOption
from buzz.api.forms.answers import LAYOUT_TYPES
from buzz.events.doctype.buzz_form.form_types import APPLIED_TO_BY_FORM_DOCTYPE, QUESTION_FIELD_NAMES

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
QUESTION_FIELDS = [*QUESTION_FIELD_NAMES, "idx"]

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
		if row.fieldtype not in LAYOUT_TYPES
	]


def form_questions(event: str, form_doctype: str) -> list:
	"""The enabled questions of the event's form of that doctype, in form order."""
	return form_questions_by_doctype(event, (form_doctype,)).get(form_doctype, [])


def form_questions_by_doctype(event: str, form_doctypes: tuple[str, ...]) -> dict[str, list]:
	"""Enabled questions for one or more form doctypes of an event, in one JOIN query."""
	form = frappe.qb.DocType("Buzz Form")
	field = frappe.qb.DocType("Buzz Form Field")
	rows = (
		frappe.qb.from_(field)
		.join(form)
		.on(form.name == field.parent)
		.select(form.form_doctype, *(field[name] for name in QUESTION_FIELDS))
		.where(
			(form.event == str(event))
			& form.form_doctype.isin(list(form_doctypes))
			& (field.parenttype == "Buzz Form")
			& (field.enabled == 1)
			& (field.is_standard == 0)
		)
		.orderby(field.idx)
	).run(as_dict=True)
	grouped: dict[str, list] = {doctype: [] for doctype in form_doctypes}
	for row in rows:
		doctype = row.pop("form_doctype")
		grouped.setdefault(doctype, []).append(row)
	return grouped


def form_logic_rules(event: str, form_doctype: str) -> str | None:
	return frappe.db.get_value("Buzz Form", {"event": event, "form_doctype": form_doctype}, "logic_rules")


def registration_questions(event: str) -> list:
	"""Booking then attendee questions, each tagged with what the booking page calls it."""
	return [
		frappe._dict(question, applied_to=applied_to)
		for form_doctype, applied_to in APPLIED_TO_BY_FORM_DOCTYPE.items()
		for question in form_questions(event, form_doctype)
	]


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

	def __init__(
		self,
		doctype: str,
		fields: list[FilterField],
		answer_parents: dict | None = None,
		event: str | None = None,
	):
		"""`answer_parents` maps a question answered on a linked record to that record's doctype
		and the list field linking to it, as a guest's booking questions sit on the booking."""
		self.doctype = doctype
		self.fields = {field.key: field for field in fields}
		self.answer_parents = answer_parents or {}
		self.event = str(event) if event is not None else None

	def frappe_filters(self, filters_json: str | None) -> list[list]:
		translated = (self.translate(*triple) for triple in self.parse(filters_json))
		return [condition for condition in translated if condition]

	def split_qb_criteria(self, filters_json: str | None, table) -> tuple[list[list], list[Criterion]]:
		"""Split filters into standard Frappe filter triples and correlated EXISTS criteria."""
		standard_filters: list[list] = []
		exists_criteria: list[Criterion] = []
		for key, operator, value in self.parse(filters_json):
			if is_blank(operator, value):
				continue
			if key == TAGS_KEY:
				exists_criteria.append(self.tags_criterion(table, operator, value))
				continue
			field = self.fields[key]
			if field.section == "question":
				doctype, link_field = self.answer_parents.get(key, (self.doctype, "name"))
				criterion = AnswerCondition(
					doctype, link_field, field, operator, value, event=self.event
				).qb_criterion(table)
				if criterion is not None:
					exists_criteria.append(criterion)
			else:
				standard_filters.append([key, operator, f"%{value}%" if "like" in operator else value])
		return standard_filters, exists_criteria

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
			return AnswerCondition(
				doctype, link_field, field, operator, value, event=self.event
			).name_filter()
		return [key, operator, f"%{value}%" if "like" in operator else value]

	def tags_criterion(self, table, operator: str, value) -> Criterion:
		values = value if isinstance(value, list) else [value]
		tag_link = frappe.qb.DocType("Buzz Tag Link")
		subquery = (
			frappe.qb.from_(tag_link)
			.select(ValueWrapper(1))
			.where(
				(tag_link.document_type == self.doctype)
				& (tag_link.document_name == table.name)
				& tag_link.tag.isin(values)
			)
		)
		criterion = ExistsCriterion(subquery)
		return criterion.negate() if operator == "not in" else criterion

	def tagged_names(self, tags: list[str]) -> list[str]:
		return frappe.get_all(
			"Buzz Tag Link",
			filters={"document_type": self.doctype, "tag": ["in", tags]},
			pluck="document_name",
		)


EVENT_SCOPED_DOCTYPES = ("Event Ticket", "Event Booking")


class AnswerCondition:
	"""One condition on a custom question, resolved to the parents whose answer matches.

	The answers live in Additional Field rows, and frappe joins a child table only once, so
	each question is looked up on its own and lands back on the list as `name in (...)`.
	"""

	def __init__(
		self,
		doctype: str,
		link_field: str,
		field: FilterField,
		operator: str,
		value,
		event: str | None = None,
	):
		self.doctype = doctype
		self.link_field = link_field
		self.field = field
		self.operator = operator
		self.values = value if isinstance(value, list) else [value]
		self.event = str(event) if event is not None else None

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

	def _answer_query(self):
		field = frappe.qb.DocType("Additional Field")
		query = frappe.qb.from_(field).where(
			(field.parenttype == self.doctype)
			& (field.parentfield == "additional_fields")
			& (field.fieldname == self.field.key)
		)
		if self.event and self.doctype in EVENT_SCOPED_DOCTYPES:
			parent_table = frappe.qb.DocType(self.doctype)
			query = (
				query.join(parent_table)
				.on(parent_table.name == field.parent)
				.where(parent_table.event == self.event)
			)
		return field, query

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
		field, query = self._answer_query()
		rows = query.select(field.parent, field.value).run(as_dict=True)
		return [row.parent for row in rows if row.value not in (None, "") and matches(convert(row.value))]

	def answered_parents(self, value=None) -> list[str]:
		field, query = self._answer_query()
		if value is None:
			query = query.where(field.value.isnotnull() & (field.value != ""))
		else:
			op, operand = value
			if op == "in":
				if not operand:
					return []
				query = query.where(field.value.isin(operand))
			elif op == "like":
				query = query.where(field.value.like(operand))
			else:
				query = query.where(field.value == operand)
		return query.select(field.parent).distinct().run(pluck=True)

	def qb_criterion(self, table) -> Criterion | None:
		outer_column = table[self.link_field]
		field = frappe.qb.DocType("Additional Field")
		if self.operator == "is":
			criterion = self._exists_criterion(
				outer_column, field, field.value.isnotnull() & (field.value != "")
			)
			return criterion if self.values[0] == "set" else criterion.negate()
		if self.field.fieldtype == "Check":
			return self.check_qb_criterion(outer_column, field)
		positive_operator = NEGATED_OPERATORS.get(self.operator, self.operator)
		value_criterion = self._value_criterion(field, positive_operator)
		criterion = self._exists_criterion(outer_column, field, value_criterion)
		return criterion.negate() if self.operator in NEGATED_OPERATORS else criterion

	def check_qb_criterion(self, outer_column, field) -> Criterion | None:
		selected_values = set(self.values)
		if self.operator == "not in":
			selected_values = {"0", "1"} - selected_values
		if len(selected_values) != 1:
			return None
		criterion = self._exists_criterion(outer_column, field, field.value.isin(CHECKED_VALUES))
		return criterion if selected_values == {"1"} else criterion.negate()

	def _exists_criterion(self, outer_column, field, value_criterion) -> ExistsCriterion:
		subquery = (
			frappe.qb.from_(field)
			.select(ValueWrapper(1))
			.where(
				(field.parenttype == self.doctype)
				& (field.parentfield == "additional_fields")
				& (field.fieldname == self.field.key)
				& (field.parent == outer_column)
				& value_criterion
			)
		)
		return ExistsCriterion(subquery)

	def _value_criterion(self, field, operator: str) -> Criterion:
		kind = kind_of(self.field.fieldtype)
		if kind in ("number", "date"):
			return self._comparison_criterion(field, kind, operator)
		if kind == "multi":
			patterns = [f'%"{option}"%' for option in self.values] + [
				f"%'{option}'%" for option in self.values
			]
			return Criterion.any([field.value.like(pattern) for pattern in patterns])
		if operator == "like":
			return field.value.like(f"%{self.values[0]}%")
		if operator == "in":
			return field.value.isin(self.values)
		return field.value == self.values[0]

	def _comparison_criterion(self, field, kind: str, operator: str) -> Criterion:
		guard = field.value.isnotnull() & (field.value != "")
		if kind == "number":
			low, high = flt(self.values[0]), flt(self.values[-1])
			guard = guard & field.value.regexp(r"^-?[0-9]+(\.[0-9]+)?$")
			column = Cast_(field.value, "DECIMAL(20, 6)")
		else:
			low, high = str(self.values[0]), str(self.values[-1])
			column = field.value
		comparisons = {
			"=": column == low,
			">": column > low,
			"<": column < low,
			"between": column.between(low, high),
		}
		return guard & comparisons[operator]
