import frappe
from frappe.utils import escape_html

from buzz.events.doctype.buzz_team.buzz_team import personal_team_of, personal_teams_enabled
from buzz.events.doctype.buzz_team.team_page import TeamPage
from buzz.www.site_header import apply_site_context

no_cache = 1


def get_context(context):
	team = get_profile_team(frappe.form_dict.username)
	apply_site_context(context)
	context.doc = team
	context.update(TeamPage(team).as_context())


def get_profile_team(username: str | None):
	"""The personal team behind /u/<username>, shown as its owner. Public once it has a published event."""
	user = get_user_by_username(username) if personal_teams_enabled() and username else None
	team = personal_team_of(user.name) if user else None
	if not team or not frappe.db.exists("Buzz Event", {"team": team, "is_published": 1}):
		raise frappe.PageDoesNotExistError

	doc = frappe.get_doc("Buzz Team", team)
	# The team page renders `about` as HTML, and a bio is plain text.
	about = escape_html(user.bio) if user.bio else None
	doc.update(
		{"team_name": user.full_name, "logo": user.user_image, "about": about, "route": f"u/{username}"}
	)
	return doc


def get_user_by_username(username: str) -> frappe._dict | None:
	fields = ["name", "full_name", "user_image", "bio"]
	return frappe.db.get_value("User", {"username": username, "enabled": 1}, fields, as_dict=True)
