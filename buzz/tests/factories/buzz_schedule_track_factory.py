from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.buzz_schedule_track.buzz_schedule_track import BuzzScheduleTrack

_fake = Faker()


class BuzzScheduleTrackFactory(BaseFactory[BuzzScheduleTrack]):
	doctype = "Buzz Schedule Track"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzScheduleFactory

		return {
			"schedule": self.overrides.get("schedule") or BuzzScheduleFactory.create().name,
			"title": f"{_fake.word().capitalize()} Hall",
		}
