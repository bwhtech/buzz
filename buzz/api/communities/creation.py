import frappe

from buzz.api.communities.exceptions import CommunitiesDisabled, LoginRequired
from buzz.api.communities.schemas import CreatedCommunity
from buzz.api.events.schemas import RouteAvailability
from buzz.api.teams import public_page
from buzz.api.teams.exceptions import InvalidTeamSlug, TeamSlugTaken


def ensure_communities_enabled() -> None:
	if not frappe.db.get_single_value("Buzz Settings", "enable_communities"):
		CommunitiesDisabled.throw()


def slug_availability(slug: str) -> RouteAvailability:
	ensure_communities_enabled()
	# No team yet, so no slug is the person's own.
	return public_page.slug_availability("", slug)


def create_community(team_name: str, slug: str) -> CreatedCommunity:
	ensure_communities_enabled()
	if frappe.session.user == "Guest":
		LoginRequired.throw()
	clean = available_slug(slug)
	team = frappe.get_doc(
		{
			"doctype": "Buzz Team",
			"team_name": team_name,
			"slug": clean,
			"is_published": 1,
			"accept_community_submissions": 1,
		}
	).insert(ignore_permissions=True)
	return CreatedCommunity(team=team.name, route=f"/{team.route}")


def available_slug(slug: str) -> str:
	clean = public_page.clean_slug(slug)
	if not clean:
		InvalidTeamSlug.throw()
	if public_page.slug_taken("", clean):
		TeamSlugTaken.throw(slug=clean)
	return clean
