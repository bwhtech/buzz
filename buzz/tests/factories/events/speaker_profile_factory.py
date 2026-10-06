from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.speaker_profile.speaker_profile import SpeakerProfile

_fake = Faker()


class SpeakerProfileFactory(BaseFactory[SpeakerProfile]):
	"""`user` is unique, so pass one from `UserFactory.create_once` to dodge the User throttle."""

	doctype = "Speaker Profile"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import UserFactory

		return {
			"user": self.overrides.get("user") or UserFactory.create().name,
			"display_name": _fake.name(),
		}
