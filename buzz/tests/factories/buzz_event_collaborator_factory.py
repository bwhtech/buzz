from functools import cached_property
from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.buzz_event_collaborator.buzz_event_collaborator import BuzzEventCollaborator
from buzz.permissions import SECTIONS

_fake = Faker()


class BuzzEventCollaboratorFactory(BaseFactory[BuzzEventCollaborator]):
	doctype = "Buzz Event Collaborator"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzEventFactory

		return {
			"event": self.overrides.get("event") or BuzzEventFactory.create("unpublished").name,
			"email": self.email,
			"details_access": "View",
		} | self.default_sections

	@property
	def default_sections(self) -> dict[str, Any]:
		# Details View alone is refused, so a row that names no section reads the guest list.
		named = any(f"{section}_access" in self.overrides for section in SECTIONS[1:])
		if named or self.overrides.get("details_access") == "Edit":
			return {}
		return {"guests_access": "View"}

	@cached_property
	def email(self) -> str:
		return self.overrides.get("email") or _fake.unique.email()

	@property
	def pending(self) -> dict[str, Any]:
		return {"status": "Pending"}

	@property
	def accepted(self) -> dict[str, Any]:
		from buzz.tests.factories import UserFactory

		return {"status": "Accepted", "user": UserFactory.create_once(self.email).name}
