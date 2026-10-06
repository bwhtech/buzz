from typing import Any

import frappe
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.sponsorship_tier.sponsorship_tier import SponsorshipTier


class SponsorshipTierFactory(BaseFactory[SponsorshipTier]):
	"""One INR price row: `validate_prices` refuses a tier without one."""

	doctype = "Sponsorship Tier"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzEventFactory

		return {
			"event": self.overrides.get("event") or BuzzEventFactory.create().name,
			"title": f"Tier {frappe.generate_hash(length=6)}",
			"prices": [{"currency": "INR", "price": 5000}],
		}
