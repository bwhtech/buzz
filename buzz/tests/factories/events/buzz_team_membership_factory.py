from typing import Any

from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.events.doctype.buzz_team_membership.buzz_team_membership import BuzzTeamMembership


class BuzzTeamMembershipFactory(BaseFactory[BuzzTeamMembership]):
	"""A Manager by default. Pass `team_role` for any other role."""

	doctype = "Buzz Team Membership"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzTeamFactory, UserFactory

		return {
			"team": self.overrides.get("team") or BuzzTeamFactory.create_owned_by().name,
			"user": self.overrides.get("user") or UserFactory.create().name,
		}
