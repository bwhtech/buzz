import frappe
from frappe import _
from frappe.website.utils import cleanup_page_name

from buzz.api.events.schemas import RouteAvailability
from buzz.api.teams.exceptions import InvalidTeamSlug, TeamSlugTaken


def clean_slug(slug: str | None) -> str:
	return cleanup_page_name(slug or "").replace("_", "-").strip("-")


def slug_taken(team: str, slug: str) -> bool:
	return bool(frappe.db.exists("Buzz Team", {"slug": slug, "name": ["!=", team]}))


def slug_availability(team: str, slug: str) -> RouteAvailability:
	"""What the settings field says while someone types. Checks the slug as it would be
	saved, so the answer matches what set_slug does."""
	clean = clean_slug(slug)
	if not clean or slug_taken(team, clean):
		return RouteAvailability(available=False, message=_("This URL is already taken"))
	return RouteAvailability(available=True, message=_("Available"))


def set_slug(doc, slug: str | None) -> None:
	"""Move the team to a new address. The route follows the slug even while the team is
	private, so publishing later serves the address the team chose."""
	if slug is None or slug == doc.slug:
		return
	clean = clean_slug(slug)
	if not clean:
		InvalidTeamSlug.throw()
	if slug_taken(doc.name, clean):
		TeamSlugTaken.throw(slug=clean)
	doc.slug = clean
	doc.route = doc.make_route()
