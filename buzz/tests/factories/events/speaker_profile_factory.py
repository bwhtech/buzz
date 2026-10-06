from typing import Any

from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.speaker_profile.speaker_profile import SpeakerProfile


class SpeakerProfileFactory(BaseFactory[SpeakerProfile]):
	"""`display_name` is fetched from the user's full name on save, so name the user instead."""

	doctype = "Speaker Profile"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import UserFactory

		return {"user": self.overrides.get("user") or UserFactory.create().name}
