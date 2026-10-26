from typing import Any

import frappe
from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.buzz_form.buzz_form import BuzzForm

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
		form.append(
			"questions",
			{
				"label": label,
				"fieldname": question.get("fieldname") or frappe.scrub(label),
				"fieldtype": "Data",
				"asked_per": question.get("asked_per") or "Attendee",
				**question,
			},
		)
		form.save(ignore_permissions=True)
		return form

	@classmethod
	def clear_questions(cls, event, form_doctype: str = "Event Booking") -> BuzzForm:
		"""Drop the event's questions: a booking commits, so a test's questions outlive it."""
		form = frappe.get_doc("Buzz Form", {"event": event, "form_doctype": form_doctype})
		form.set("questions", [])
		form.save(ignore_permissions=True)
		return form

	@classmethod
	def set_registration_cutoff(cls, event, close_at=None):
		"""None leaves registrations open until the event ends."""
		frappe.db.set_value(
			"Buzz Form", {"event": event, "form_doctype": "Event Booking"}, "auto_close_at", close_at
		)
