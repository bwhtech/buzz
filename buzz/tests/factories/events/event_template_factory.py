from typing import Any

import frappe
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.event_template.event_template import EventTemplate


class EventTemplateFactory(BaseFactory[EventTemplate]):
	"""Category and host are set: an event made from the template needs both."""

	doctype = "Event Template"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzTeamFactory, EventCategoryFactory, EventHostFactory

		team = self.overrides.get("team") or BuzzTeamFactory.create_owned_by().name
		# Named after `template_name`, and rows outlive a run, so a hash beats Faker's `unique`.
		return {
			"template_name": f"Template {frappe.generate_hash(length=8)}",
			"team": team,
			"category": self.overrides.get("category") or EventCategoryFactory.create().name,
			"host": self.overrides.get("host") or EventHostFactory.create(team=team).name,
		}
