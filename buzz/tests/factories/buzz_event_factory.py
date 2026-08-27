from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.buzz_event.buzz_event import BuzzEvent

_fake = Faker()


class BuzzEventFactory(BaseFactory[BuzzEvent]):
	"""
	Builds a published online event with a fresh team, category and host. Pass
	`team=`, `category=` or `host=` to reuse existing records instead.

	`route` is left unset on purpose — `validate_route` derives it from the
	unique title and deduplicates it.
	"""

	doctype = "Buzz Event"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories.buzz_team_factory import BuzzTeamFactory
		from buzz.tests.factories.event_category_factory import EventCategoryFactory
		from buzz.tests.factories.event_host_factory import EventHostFactory

		team = self.overrides.get("team") or BuzzTeamFactory.create_owned_by().name
		return {
			"title": f"Event {_fake.unique.catch_phrase()}",
			"team": team,
			"category": self.overrides.get("category") or EventCategoryFactory.create().name,
			"host": self.overrides.get("host") or EventHostFactory.create(team=team).name,
			"start_date": "2030-01-01",
			"end_date": "2030-01-01",
			"start_time": "10:00:00",
			"end_time": "18:00:00",
			"medium": "Online",
			"is_published": 1,
		}
