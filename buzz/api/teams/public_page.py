import frappe
from frappe.website.utils import cleanup_page_name

from buzz.api.teams.exceptions import InvalidTeamSlug, TeamSlugTaken


def set_slug(doc, slug: str | None) -> None:
	"""Move the team to a new address. The route follows the slug even while the team is
	private, so publishing later serves the address the team chose."""
	if slug is None or slug == doc.slug:
		return
	clean = cleanup_page_name(slug).replace("_", "-").strip("-")
	if not clean:
		InvalidTeamSlug.throw()
	if frappe.db.exists("Buzz Team", {"slug": clean, "name": ["!=", doc.name]}):
		TeamSlugTaken.throw(slug=clean)
	doc.slug = clean
	doc.route = doc.make_route()
