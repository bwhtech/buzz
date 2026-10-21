from typing import Any

from faker import Faker
from frappe.utils import add_days, today
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.community_event_request.community_event_request import CommunityEventRequest

_fake = Faker()


class CommunityEventRequestFactory(BaseFactory[CommunityEventRequest]):
	"""A pending request to list an event hosted on another site."""

	doctype = "Community Event Request"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzTeamFactory

		day = add_days(today(), 20)
		return {
			"community": self.overrides.get("community")
			or BuzzTeamFactory.create_owned_by(None, "community").name,
			"is_external_event": 1,
			"event_title": f"Meetup {_fake.unique.catch_phrase()}",
			"event_url": "https://example.com/meetup",
			"host": _fake.company(),
			"event_location": _fake.city(),
			"start_datetime": f"{day} 18:00:00",
			"end_datetime": f"{day} 20:00:00",
		}

	@property
	def approved(self) -> dict[str, Any]:
		return {"status": "Approved"}
