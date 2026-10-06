from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.additional_event_page.additional_event_page import AdditionalEventPage

_fake = Faker()


class AdditionalEventPageFactory(BaseFactory[AdditionalEventPage]):
	doctype = "Additional Event Page"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzEventFactory

		return {
			"event": self.overrides.get("event") or BuzzEventFactory.create().name,
			"title": _fake.unique.catch_phrase(),
			"content": f"<p>{_fake.sentence()}</p>",
		}

	@property
	def published(self) -> dict[str, Any]:
		return {"is_published": 1}
