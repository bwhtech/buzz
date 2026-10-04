from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.buzz_team.buzz_team import BuzzTeam

_fake = Faker()

# Shared so teams built as link targets do not hit the User creation throttle.
LINK_TEAM_OWNER = "factory-team-owner@example.com"


class BuzzTeamFactory(BaseFactory[BuzzTeam]):
	doctype = "Buzz Team"

	@classmethod
	def create_owned_by(cls, user: str | None = None, **overrides: Any) -> BuzzTeam:
		"""Prefer over `create()`: an Administrator-owned test team becomes its default team."""
		from buzz.tests.factories.user_factory import UserFactory

		owner = user or UserFactory.create_once(LINK_TEAM_OWNER).name
		return cls.create(flags={"owner_user": owner}, **overrides)

	@property
	def default_attributes(self) -> dict[str, Any]:
		return {"team_name": f"{_fake.unique.word().capitalize()} Team"}
