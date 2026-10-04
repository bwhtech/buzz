from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.buzz.doctype.buzz_custom_field.buzz_custom_field import BuzzCustomField

_fake = Faker()


class BuzzCustomFieldFactory(BaseFactory[BuzzCustomField]):
	"""An enabled Data field on the booking form."""

	doctype = "Buzz Custom Field"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories.buzz_event_factory import BuzzEventFactory

		return {
			"event": self.overrides.get("event") or BuzzEventFactory.create().name,
			"label": _fake.word().capitalize(),
		}
