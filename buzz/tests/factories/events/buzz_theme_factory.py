from typing import Any

import frappe
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.buzz_theme.buzz_theme import BuzzTheme

STANDARD_THEME = "Classic"


class BuzzThemeFactory(BaseFactory[BuzzTheme]):
	"""A custom copy of Classic, so every required token is present."""

	doctype = "Buzz Theme"

	@property
	def default_attributes(self) -> dict[str, Any]:
		return {
			"theme_name": f"Theme {frappe.generate_hash(length=8)}",
			"tokens": standard_tokens(),
		}


def standard_tokens() -> list[dict]:
	return frappe.get_all(
		"Buzz Theme Token",
		filters={"parenttype": "Buzz Theme", "parent": STANDARD_THEME},
		fields=["token", "type", "value", "dark_value"],
		order_by="idx",
	)
