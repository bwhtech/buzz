from typing import Any

import frappe
from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.buzz_marketing.doctype.buzz_campaign.buzz_campaign import BuzzCampaign

_fake = Faker()


class BuzzCampaignFactory(BaseFactory[BuzzCampaign]):
	"""Disabled by default: an enabled campaign refuses to save unless Frappe CRM is installed."""

	doctype = "Buzz Campaign"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzTeamFactory

		# Prompt-autonamed, and rows outlive a run, so a hash beats Faker's per-process `unique`.
		name = f"Campaign {frappe.generate_hash(length=8)}"
		return {
			"name": name,
			"title": name,
			"description": _fake.sentence(),
			"team": self.overrides.get("team") or BuzzTeamFactory.create_owned_by().name,
		}
