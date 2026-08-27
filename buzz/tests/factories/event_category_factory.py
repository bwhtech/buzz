from typing import Any

import frappe
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.event_category.event_category import EventCategory


class EventCategoryFactory(BaseFactory[EventCategory]):
	doctype = "Event Category"

	@property
	def default_attributes(self) -> dict[str, Any]:
		# autoname is "prompt": the name has to come in with the attributes, and it is
		# the primary key. Faker's `unique` only dedupes within a process, and these
		# rows outlive a run, so the suffix is a hash.
		return {"name": f"Category {frappe.generate_hash(length=8)}"}
