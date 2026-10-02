# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr

from buzz.events.doctype.buzz_price.buzz_price import validate_unique_currencies


class SponsorshipTier(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buzz.events.doctype.buzz_price.buzz_price import BuzzPrice

		enabled: DF.Check
		event: DF.Link
		perks: DF.SmallText | None
		prices: DF.Table[BuzzPrice]
		slots: DF.Int
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		self.validate_event_is_unchanged()
		self.validate_prices()

	def validate_event_is_unchanged(self):
		before = self.get_doc_before_save()
		if before and cstr(before.event) != cstr(self.event):
			frappe.throw(
				_("A sponsorship tier cannot be moved to another event."), frappe.CannotChangeConstantError
			)

	def validate_prices(self):
		if not self.prices:
			frappe.throw(_("Add at least one price to the sponsorship tier."))
		validate_unique_currencies(self.prices)

	def price_for(self, currency: str | None = None):
		"""The price row for a currency; the first row is the default."""
		if not currency:
			return self.prices[0]
		for row in self.prices:
			if row.currency == currency:
				return row
		frappe.throw(_("This sponsorship tier has no price in {0}.").format(currency))


def default_price(tier: frappe._dict) -> float:
	"""Sort key for tiers fetched with their `prices` rows."""
	return tier.prices[0].price
