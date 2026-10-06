from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.event_sponsor.event_sponsor import EventSponsor

_fake = Faker()


class EventSponsorFactory(BaseFactory[EventSponsor]):
	"""A sponsor on a new tier of `event`, with no enquiry behind it."""

	doctype = "Event Sponsor"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzEventFactory, SponsorshipTierFactory

		event = self.overrides.get("event") or BuzzEventFactory.create().name
		return {
			"event": event,
			"tier": self.overrides.get("tier") or SponsorshipTierFactory.create(event=event).name,
			"company_name": _fake.company(),
			"company_logo": "/files/logo.png",
		}
