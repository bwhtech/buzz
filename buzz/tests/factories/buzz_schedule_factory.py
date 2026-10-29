from typing import Any

from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.buzz_schedule.buzz_schedule import BuzzSchedule


class BuzzScheduleFactory(BaseFactory[BuzzSchedule]):
	doctype = "Buzz Schedule"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzEventFactory

		return {"event": self.overrides.get("event") or str(BuzzEventFactory.create().name)}
