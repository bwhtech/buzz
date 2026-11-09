"""The team a new user joined through an invite, shown in place of the fork."""

import frappe
from frappe.utils import get_fullname, today

from buzz.api.onboarding.schemas import InvitedTeam
from buzz.permissions import HUMAN_MEMBER_FILTERS, INTEGRATION_ROLE


def invited_team(user: str) -> InvitedTeam | None:
	membership = frappe.db.get_value(
		"Buzz Team Membership",
		{"user": user, "enabled": 1, "team_role": ("not in", ("Owner", INTEGRATION_ROLE))},
		["team", "team_role"],
		as_dict=True,
		order_by="creation asc",
	)
	if not membership or frappe.db.get_value("Buzz Team", membership.team, "is_personal"):
		return None
	team = frappe.db.get_value("Buzz Team", membership.team, ["name", "team_name", "logo"], as_dict=True)
	return InvitedTeam(
		**team,
		team_role=membership.team_role,
		invited_by=inviter(user, team.name),
		member_count=frappe.db.count("Buzz Team Membership", {"team": team.name, **HUMAN_MEMBER_FILTERS}),
		upcoming_event_count=frappe.db.count(
			"Buzz Event", {"team": team.name, "is_published": 1, "start_date": (">=", today())}
		),
	)


def inviter(user: str, team: str) -> str | None:
	invited_by = frappe.db.get_value(
		"User Invitation", {"email": user, "buzz_team": team, "status": "Accepted"}, "invited_by"
	)
	return get_fullname(invited_by) if invited_by else None
