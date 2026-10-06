from typing import Any

import frappe
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.offline_payment_method.offline_payment_method import OfflinePaymentMethod


class OfflinePaymentMethodFactory(BaseFactory[OfflinePaymentMethod]):
	"""Enabled by default. Titles are unique per event."""

	doctype = "Offline Payment Method"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzEventFactory

		return {
			"event": self.overrides.get("event") or BuzzEventFactory.create().name,
			"title": f"Bank Transfer {frappe.generate_hash(length=6)}",
		}
