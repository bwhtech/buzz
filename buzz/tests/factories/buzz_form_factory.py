from typing import Any

import frappe
from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.api.forms.conditions import parse_rules
from buzz.events.doctype.buzz_form.buzz_form import BuzzForm
from buzz.events.doctype.buzz_form.form_types import TEMPLATE_CONDITION_ACTIONS, template_rules

_fake = Faker()


class BuzzFormFactory(BaseFactory[BuzzForm]):
	doctype = "Buzz Form"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzEventFactory

		return {
			"title": f"Form {_fake.unique.catch_phrase()}",
			"event": self.overrides.get("event") or BuzzEventFactory.create().name,
			# Talk Proposal is one per event; every event already has one.
			"form_doctype": self.overrides.get("form_doctype") or "Event Feedback",
			"route": f"form-{frappe.generate_hash(length=6)}",
		}

	@classmethod
	def add_question(cls, event, form_doctype: str = "Event Booking", **question) -> BuzzForm:
		"""Append an enabled Data question to the event's form of that doctype."""
		form = frappe.get_doc("Buzz Form", {"event": event, "form_doctype": form_doctype})
		label = question.pop("label", _fake.word().capitalize())
		fieldname = question.pop("fieldname", None) or frappe.scrub(label)
		cls.append_question(form, **{"label": label, "fieldname": fieldname, "fieldtype": "Data", **question})
		form.save(ignore_permissions=True)
		return form

	@classmethod
	def append_question(cls, form, **question) -> None:
		"""Append a question; `depends_on` and `mandatory_depends_on` become rules acting on it alone."""
		conditions = {key: question.pop(key) for key in TEMPLATE_CONDITION_ACTIONS if key in question}
		form.append("questions", question)
		rules = parse_rules(form.logic_rules) + template_rules(
			frappe._dict(conditions, fieldname=question.get("fieldname"))
		)
		form.logic_rules = frappe.as_json(rules, indent=None) if rules else None

	@classmethod
	def clear_questions(cls, event, form_doctype: str = "Event Booking") -> BuzzForm:
		"""Drop the event's questions: a booking commits, so a test's questions outlive it."""
		form = frappe.get_doc("Buzz Form", {"event": event, "form_doctype": form_doctype})
		form.set("questions", [])
		form.logic_rules = None
		form.save(ignore_permissions=True)
		return form

	@classmethod
	def set_registration_cutoff(cls, event, close_at=None):
		"""None leaves registrations open until the event ends."""
		frappe.db.set_value(
			"Buzz Form", {"event": event, "form_doctype": "Event Booking"}, "auto_close_at", close_at
		)
