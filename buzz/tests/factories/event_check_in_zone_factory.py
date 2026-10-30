from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.event_check_in_zone.event_check_in_zone import EventCheckinZone

_fake = Faker()


class EventCheckinZoneFactory(BaseFactory[EventCheckinZone]):
	"""An extra, enabled zone. Every event already has its default zone."""

	doctype = "Event Check-in Zone"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzEventFactory

		return {
			"event": self.overrides.get("event") or BuzzEventFactory.create().name,
			"title": f"Zone {_fake.word().capitalize()}",
		}

	@property
	def once_per_event(self) -> dict[str, Any]:
		return {"repeat_rule": "Once per event"}

	@property
	def disabled(self) -> dict[str, Any]:
		return {"enabled": 0}
