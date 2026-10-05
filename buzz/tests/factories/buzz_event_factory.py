from typing import Any

from faker import Faker
from frappe.utils import add_days, today
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.buzz_event.buzz_event import BuzzEvent

_fake = Faker()


class BuzzEventFactory(BaseFactory[BuzzEvent]):
	"""A published online event. `route` comes from the title in `validate_route`."""

	doctype = "Buzz Event"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories.buzz_team_factory import BuzzTeamFactory
		from buzz.tests.factories.event_category_factory import EventCategoryFactory
		from buzz.tests.factories.event_host_factory import EventHostFactory

		team = self.overrides.get("team") or BuzzTeamFactory.create_owned_by().name
		# Registrations close once an event ends, so a fixed date would expire.
		event_date = add_days(today(), 30)
		return {
			"title": f"Event {_fake.unique.catch_phrase()}",
			"team": team,
			"category": self.overrides.get("category") or EventCategoryFactory.create().name,
			"host": self.overrides.get("host") or EventHostFactory.create(team=team).name,
			"start_date": event_date,
			"end_date": event_date,
			"start_time": "10:00:00",
			"end_time": "18:00:00",
			"medium": "Online",
			"is_published": 1,
		}
