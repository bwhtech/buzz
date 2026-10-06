from typing import Any

import frappe
from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.event_talk.event_talk import EventTalk

_fake = Faker()


class EventTalkFactory(BaseFactory[EventTalk]):
	"""A talk with no speakers. Pass `speakers=[{"speaker": profile}]` for some."""

	doctype = "Event Talk"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzEventFactory

		return {
			"event": self.overrides.get("event") or BuzzEventFactory.create().name,
			"title": _fake.sentence(nb_words=4).rstrip("."),
			"submitted_by": frappe.session.user,
		}
