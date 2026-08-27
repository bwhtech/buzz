from typing import Any

import frappe
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.event_host.event_host import EventHost


class EventHostFactory(BaseFactory[EventHost]):
	doctype = "Event Host"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories.buzz_team_factory import BuzzTeamFactory

		# autoname is "prompt": the name is the primary key, and these rows outlive a
		# run, so the suffix is a hash rather than Faker's per-process `unique`.
		return {
			"name": f"Host {frappe.generate_hash(length=8)}",
			"team": self.overrides.get("team") or BuzzTeamFactory.create_owned_by().name,
		}
