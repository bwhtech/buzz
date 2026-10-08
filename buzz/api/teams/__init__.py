import frappe

from buzz.api.events.schemas import RouteAvailability
from buzz.api.teams import invitations, public_page, services
from buzz.api.teams.schemas import InviteOutcome, TeamOption, TeamOverview
from buzz.events.doctype.buzz_team_settings.buzz_team_settings import feature_flags


@frappe.whitelist()
def get_my_teams() -> list[TeamOption]:
	"""Teams the session user belongs to, for the teams page and the settings dialog.

	Reads past permissions on purpose: Buzz Team is readable by Event Manager only, while a
	Frontdesk or Viewer member still has to see the team they work in. Rows are filtered to
	the session user's own enabled memberships.
	"""
	membership = frappe.qb.DocType("Buzz Team Membership")
	team = frappe.qb.DocType("Buzz Team")

	my_teams = (
		frappe.qb.from_(membership)
		.inner_join(team)
		.on(team.name == membership.team)
		.select(
			team.name,
			team.team_name,
			team.logo,
			team.slug,
			team.is_published,
			team.accept_community_submissions,
			team.short_description,
			membership.team_role,
		)
		.where((membership.user == frappe.session.user) & (membership.enabled == 1))
	).run(as_dict=True)
	event_counts = services.upcoming_event_counts([my_team.name for my_team in my_teams])
	return [team_option(my_team, event_counts.get(my_team.name, 0)) for my_team in my_teams]


def team_option(my_team: dict, upcoming_event_count: int) -> TeamOption:
	return TeamOption(
		**my_team,
		upcoming_event_count=upcoming_event_count,
		members=services.members_of(my_team.name),
		feature_flags=feature_flags(my_team.name),
	)


@frappe.whitelist()
def get_team_overview(team: str) -> TeamOverview:
	return services.team_overview(team)


@frappe.whitelist(methods=["POST"])
def remove_members(team: str, users: list[str]) -> None:
	services.remove_members(team, users)


@frappe.whitelist(methods=["POST"])
def change_roles(team: str, users: list[str], team_role: str) -> None:
	services.change_roles(team, users, team_role)


@frappe.whitelist(methods=["POST"])
def invite_members(team: str, invites: list[dict]) -> list[InviteOutcome]:
	return invitations.invite_members(team, invites)


@frappe.whitelist(methods=["POST"])
def update_team(team: str, team_name: str, logo: str | None = None) -> None:
	services.update_team(team, team_name, logo)


@frappe.whitelist(methods=["POST"])
def update_public_page(
	team: str,
	is_published: bool,
	links: list[dict],
	short_description: str | None = None,
	about: str | None = None,
	accept_community_submissions: bool = False,
	slug: str | None = None,
) -> None:
	services.update_public_page(
		team, is_published, links, short_description, about, accept_community_submissions, slug
	)


@frappe.whitelist()
def check_team_slug(team: str, slug: str) -> RouteAvailability:
	"""Whether a team can move to this address. `team` is the one being edited."""
	return public_page.slug_availability(team, slug)


@frappe.whitelist(methods=["POST"])
def update_tax_details(team: str, legal_name: str, tax_id: str, billing_address: str) -> None:
	services.update_tax_details(team, legal_name, tax_id, billing_address)


@frappe.whitelist(methods=["POST"])
def resend_invite(team: str, email: str) -> None:
	invitations.resend_invite(team, email)


@frappe.whitelist(methods=["POST"])
def retract_invite(team: str, email: str) -> None:
	invitations.retract_invite(team, email)
