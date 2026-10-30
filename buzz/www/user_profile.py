import frappe
from frappe.utils import escape_html

from buzz.events.doctype.buzz_team.buzz_team import personal_team_of, personal_teams_enabled
from buzz.events.doctype.buzz_team.team_page import TeamPage, group_by_day
from buzz.www.event.index import public_links
from buzz.www.site_header import apply_site_context

no_cache = 1


def get_context(context):
	user = get_profile_user(frappe.form_dict.username)
	team = get_profile_team(user)
	apply_site_context(context)
	context.update(ProfilePage(user, team).as_context())


def get_profile_user(username: str | None) -> frappe._dict:
	user = get_user_by_username(username) if personal_teams_enabled() and username else None
	if not user:
		raise frappe.PageDoesNotExistError
	return user


def get_profile_team(user: frappe._dict):
	"""The personal team behind /u/<username>, shown as its owner. Public once it has a published event."""
	team = personal_team_of(user.name)
	if not team or not frappe.db.exists("Buzz Event", {"team": team, "is_published": 1}):
		raise frappe.PageDoesNotExistError

	doc = frappe.get_doc("Buzz Team", team)
	# Page meta reads `about` as HTML, and a bio is plain text.
	about = escape_html(user.bio) if user.bio else None
	doc.update({"logo": user.user_image, "about": about, "route": f"u/{user.username}"})
	return doc


def get_user_by_username(username: str) -> frappe._dict | None:
	fields = ["name", "username", "full_name", "user_image", "bio", "location"]
	return frappe.db.get_value("User", {"username": username, "enabled": 1}, fields, as_dict=True)


class ProfilePage:
	"""Context for /u/<username>: the owner, their links and the personal team's events."""

	def __init__(self, user: frappe._dict, team):
		self.user = user
		self.team_page = TeamPage(team)

	def as_context(self) -> dict:
		return {
			"title": self.user.full_name,
			"meta": self.team_page.meta(),
			"profile": self.user,
			"links": public_links(self.team_page.team.links),
			"upcoming_days": self.days(self.team_page.upcoming_events),
			"past_days": self.days(self.team_page.past_events),
		}

	def days(self, events: list) -> list[dict]:
		return group_by_day([self.team_page.card(event) for event in events])
