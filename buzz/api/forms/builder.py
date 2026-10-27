from typing import TYPE_CHECKING

import frappe

from buzz.api.forms.fields import build_field, get_renderable_fields, system_exclude_fields
from buzz.api.forms.schemas import DoctypeField, FormBuilderFields

if TYPE_CHECKING:
	from buzz.events.doctype.buzz_form.buzz_form import BuzzForm


class FormBuilderService:
	"""What the dashboard's form builder needs beyond the Buzz Form document itself."""

	def __init__(self, form: str):
		self.form: BuzzForm = frappe.get_doc("Buzz Form", form)
		self.form.check_permission("read")

	def fields(self) -> FormBuilderFields:
		# Imported here: form_types reads this package, so a module-level import cycles.
		from buzz.events.doctype.buzz_form.form_types import form_type

		doctype = self.form.form_doctype
		kind = form_type(doctype)
		offered = kind.standard_fields(doctype)
		return FormBuilderFields(
			fields=[
				self.doctype_field(df, fieldname in offered, df.reqd or fieldname in kind.locked_fieldnames)
				for fieldname, df in get_renderable_fields(doctype, system_exclude_fields(doctype)).items()
			]
		)

	def doctype_field(self, df, offered: bool, locked: bool) -> DoctypeField:
		field = build_field(df, self.form.event)
		return DoctypeField(
			fieldname=df.fieldname,
			fieldtype=df.fieldtype,
			label=field["label"],
			options=df.options if df.fieldtype == "Select" else None,
			link_options=field.get("link_options"),
			offered=offered,
			locked=bool(locked),
		)
