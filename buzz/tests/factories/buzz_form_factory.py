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
