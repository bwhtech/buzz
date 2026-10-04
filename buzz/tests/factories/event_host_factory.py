from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.event_host.event_host import EventHost

_fake = Faker()


class EventHostFactory(BaseFactory[EventHost]):
	doctype = "Event Host"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories.buzz_team_factory import BuzzTeamFactory

		return {
			"host_name": _fake.company(),
			"team": self.overrides.get("team") or BuzzTeamFactory.create_owned_by().name,
		}
