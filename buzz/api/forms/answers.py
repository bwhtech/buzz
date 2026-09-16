import json
import math

import frappe
from frappe import _
from frappe.utils import cstr, getdate, validate_email_address, validate_phone_number_with_country_code


class CustomAnswers:
	def __init__(self, definitions):
		self.definitions = {row.fieldname: row for row in definitions if row.enabled}

	def rows(self, values: dict) -> list[dict]:
		if not isinstance(values, dict) or values.keys() - self.definitions.keys():
			frappe.throw(_("Answers contain unknown questions."))
		rows = []
		for key, field in self.definitions.items():
			value = values.get(key)
			if value is None or value == "" or value == []:
				if field.mandatory:
					frappe.throw(_("{0} is required.").format(field.label), frappe.MandatoryError)
				continue
			self.validate_value(field, value)
			if field.fieldtype == "Check":
				value = int(value)
			rows.append(
				{
					"fieldname": key,
					"label": field.label,
					"fieldtype": field.fieldtype,
					"value": json.dumps(value) if isinstance(value, list) else cstr(value),
				}
			)
		return rows

	def validate_value(self, field, value):
		kind = field.fieldtype
		if kind == "Multi Select":
			if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
				self.invalid(field)
			self.validate_options(field, value)
		elif kind in ("Number", "Rating"):
			self.validate_number(field, value)
		elif kind == "Check":
			if value not in (0, 1, "0", "1", False, True):
				self.invalid(field)
		else:
			if not isinstance(value, str):
				self.invalid(field)
			self.validate_text(field, value)

	def validate_text(self, field, value):
		if field.fieldtype == "Email":
			validate_email_address(value, throw=True)
		elif field.fieldtype == "Phone":
			validate_phone_number_with_country_code(value, field.label)
		elif field.fieldtype == "Select":
			self.validate_options(field, [value])
		elif field.fieldtype == "Date":
			getdate(value)

	def validate_options(self, field, values):
		options = (field.options or "").splitlines()
		if any(value not in options for value in values):
			self.invalid(field)

	def validate_number(self, field, value):
		try:
			number = float(value)
		except (TypeError, ValueError):
			self.invalid(field)
		if isinstance(value, bool) or not math.isfinite(number):
			self.invalid(field)
		if field.fieldtype == "Rating" and not 0 <= number <= 1:
			self.invalid(field)

	def invalid(self, field):
		frappe.throw(_("Invalid answer for {0}.").format(field.label))
