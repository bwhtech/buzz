from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.buzz_team.buzz_team import BuzzTeam

_fake = Faker()

# One reusable owner for teams built as a link target. A fresh user per team runs
# the suite into Frappe's User creation throttle.
LINK_TEAM_OWNER = "factory-team-owner@example.com"


class BuzzTeamFactory(BaseFactory[BuzzTeam]):
	doctype = "Buzz Team"

	@classmethod
	def create_owned_by(cls, user: str | None = None, **overrides: Any) -> BuzzTeam:
		"""
		Give the team an Owner membership for `user`, defaulting to a shared
		throwaway owner.

		Prefer this over a bare `create()`: a plain insert makes the session user the
		Owner, and an Administrator-owned team leaks into
		`create_default_team_for("Administrator")` for every later run on the site.

		`owner_user` is a flag, and flags only reach the document through overrides.
		"""
		from buzz.tests.factories.user_factory import UserFactory

		owner = user or UserFactory.create_once(LINK_TEAM_OWNER).name
		return cls.create(flags={"owner_user": owner}, **overrides)

	@property
	def default_attributes(self) -> dict[str, Any]:
		return {"team_name": f"{_fake.unique.word().capitalize()} Team"}
