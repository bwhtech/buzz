from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.buzz_schedule_item_type.buzz_schedule_item_type import BuzzScheduleItemType

_fake = Faker()


class BuzzScheduleItemTypeFactory(BaseFactory[BuzzScheduleItemType]):
	"""A team's own item type; the standard ones ship as fixtures."""

	doctype = "Buzz Schedule Item Type"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzTeamFactory

		return {
			"team": self.overrides.get("team") or BuzzTeamFactory.create_owned_by().name,
			"title": _fake.word().capitalize(),
		}
