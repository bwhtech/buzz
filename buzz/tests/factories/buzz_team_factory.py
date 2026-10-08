from typing import Any

import frappe
from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.buzz_team.buzz_team import BuzzTeam
from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import PAID_EVENTS_FLAG

_fake = Faker()

# Shared so teams built as link targets do not hit the User creation throttle.
LINK_TEAM_OWNER = "factory-team-owner@example.com"


class BuzzTeamFactory(BaseFactory[BuzzTeam]):
	doctype = "Buzz Team"

	@classmethod
	def create_owned_by(cls, user: str | None = None, *traits: str, **overrides: Any) -> BuzzTeam:
		"""Prefer over `create()`: an Administrator-owned test team becomes its default team."""
		from buzz.tests.factories import UserFactory

		owner = user or UserFactory.create_once(LINK_TEAM_OWNER).name
		team = cls.create(*traits, flags={"owner_user": owner}, **overrides)
		# Paid tickets are the common case in tests; a test about the flag turns it off.
		cls.set_settings(team.name, {PAID_EVENTS_FLAG: 1})
		return team

	@classmethod
	def set_settings(cls, team: str, values: dict[str, Any]):
		"""Not a Single, so `change_settings` cannot set it."""
		frappe.db.set_value("Buzz Team Settings", team, values)
		frappe.clear_document_cache("Buzz Team Settings", team)

	@property
	def default_attributes(self) -> dict[str, Any]:
		return {"team_name": f"{_fake.word().capitalize()} Team"}

	@property
	def community(self) -> dict[str, Any]:
		return {"is_published": 1, "accept_community_submissions": 1}
