from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.event_venue.event_venue import EventVenue

_fake = Faker()


class EventVenueFactory(BaseFactory[EventVenue]):
	doctype = "Event Venue"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzTeamFactory

		return {
			"venue_name": f"{_fake.company()} Hall",
			"address": _fake.address(),
			"team": self.overrides.get("team") or BuzzTeamFactory.create_owned_by().name,
		}
