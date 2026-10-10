from typing import Any

import frappe
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.buzz_tag.buzz_tag import BuzzTag


class BuzzTagFactory(BaseFactory[BuzzTag]):
	"""A sponsor tag on a new team unless told otherwise."""

	doctype = "Buzz Tag"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzTeamFactory

		return {
			"team": self.overrides.get("team") or BuzzTeamFactory.create_owned_by().name,
			"document_type": "Event Sponsor",
			# Unique within a team and record type, and teams outlive the per-class rollback.
			"label": f"Tag {frappe.generate_hash(length=8)}",
		}
