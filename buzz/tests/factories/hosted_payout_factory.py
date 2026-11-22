from typing import Any

from frappe.utils import today
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.hosted_payments.doctype.hosted_payout.hosted_payout import HostedPayout


class HostedPayoutFactory(BaseFactory[HostedPayout]):
	"""A draft payout of today's INR payments."""

	doctype = "Hosted Payout"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzTeamFactory

		return {
			"team": self.overrides.get("team") or BuzzTeamFactory.create_owned_by().name,
			"from_date": today(),
			"to_date": today(),
			"currency": "INR",
		}
