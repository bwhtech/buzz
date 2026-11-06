from typing import Any

import frappe
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.buzz_theme.buzz_theme import BuzzTheme, default_tokens


class BuzzThemeFactory(BaseFactory[BuzzTheme]):
	"""A custom copy of the default standard theme, so every required token is present."""

	doctype = "Buzz Theme"

	@property
	def default_attributes(self) -> dict[str, Any]:
		return {
			"theme_name": f"Theme {frappe.generate_hash(length=8)}",
			"tokens": default_tokens(),
		}
