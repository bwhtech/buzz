import json
import math
from enum import Enum

import frappe
from frappe import _
from frappe.utils import cstr, getdate, validate_email_address, validate_phone_number_with_country_code

from buzz.api.forms.exceptions import InvalidAnswer, UnknownQuestions


class QuestionType(str, Enum):
	"""Mirrors the fieldtype options on Buzz Form Field."""

	DATA = "Data"
	CHECK = "Check"
	SMALL_TEXT = "Small Text"
	PHONE = "Phone"
	EMAIL = "Email"
	SELECT = "Select"
	DATE = "Date"
	NUMBER = "Number"
	MULTI_SELECT = "Multi Select"
	RATING = "Rating"
	ATTACH = "Attach"
	ATTACH_IMAGE = "Attach Image"


CHECK_VALUES = (0, 1, "0", "1", False, True)


class CustomAnswers:
	"""Validate submitted answers against the question definitions on a form."""

	def __init__(self, definitions):
		self.definitions = {row.fieldname: row for row in definitions if row.enabled}

	def rows(self, values: dict) -> list[dict]:
		"""Return `additional_fields` rows, rejecting anything the form did not ask for."""
		if not isinstance(values, dict) or values.keys() - self.definitions.keys():
			UnknownQuestions.throw()
		rows = []
		for fieldname, question in self.definitions.items():
			value = values.get(fieldname)
			if value is None or value == "" or value == []:
				if question.mandatory:
					frappe.throw(_("{0} is required.").format(question.label), frappe.MandatoryError)
				continue
			self.validate_value(question, value)
			if question.fieldtype == QuestionType.CHECK:
				value = int(value)
			rows.append(
				{
					"fieldname": fieldname,
					"label": question.label,
					"fieldtype": question.fieldtype,
					"value": json.dumps(value) if isinstance(value, list) else cstr(value),
				}
			)
		return rows

	def validate_value(self, question, value):
		fieldtype = question.fieldtype
		if fieldtype == QuestionType.MULTI_SELECT:
			if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
				self.invalid(question)
			self.validate_options(question, value)
		elif fieldtype in (QuestionType.NUMBER, QuestionType.RATING):
			self.validate_number(question, value)
		elif fieldtype == QuestionType.CHECK:
			if value not in CHECK_VALUES:
				self.invalid(question)
		else:
			if not isinstance(value, str):
				self.invalid(question)
			self.validate_text(question, value)

	def validate_text(self, question, value):
		if question.fieldtype == QuestionType.EMAIL:
			validate_email_address(value, throw=True)
		elif question.fieldtype == QuestionType.PHONE:
			validate_phone_number_with_country_code(value, question.label)
		elif question.fieldtype == QuestionType.SELECT:
			self.validate_options(question, [value])
		elif question.fieldtype == QuestionType.DATE:
			getdate(value)

	def validate_options(self, question, values):
		options = (question.options or "").splitlines()
		if any(value not in options for value in values):
			self.invalid(question)

	def validate_number(self, question, value):
		try:
			number = float(value)
		except (TypeError, ValueError):
			self.invalid(question)
		if isinstance(value, bool) or not math.isfinite(number):
			self.invalid(question)
		if question.fieldtype == QuestionType.RATING and not 0 <= number <= 1:
			self.invalid(question)

	def invalid(self, question):
		InvalidAnswer.throw(label=question.label)
