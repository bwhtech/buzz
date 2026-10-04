from typing import Any

import frappe
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.event_category.event_category import EventCategory


class EventCategoryFactory(BaseFactory[EventCategory]):
	doctype = "Event Category"

	@property
	def default_attributes(self) -> dict[str, Any]:
		# Prompt-autonamed, and rows outlive a run, so a hash beats Faker's per-process `unique`.
		return {"name": f"Category {frappe.generate_hash(length=8)}"}
