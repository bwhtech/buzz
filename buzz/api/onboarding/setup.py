"""Records the community the onboarding step creates."""

import frappe

from buzz.api.communities.creation import create_community, ensure_communities_enabled
from buzz.api.onboarding.schemas import CommunityDraft
from buzz.api.teams import public_page


def _owned_community_row(user: str, fields: list[str]):
	owned = frappe.get_all(
		"Buzz Team Membership", filters={"user": user, "team_role": "Owner", "enabled": 1}, pluck="team"
	)
	if not owned:
		return None
	return frappe.db.get_value(
		"Buzz Team",
		{"name": ("in", owned), "is_personal": 0},
		fields,
		as_dict=True,
		order_by="creation desc",
	)


def owned_community(user: str) -> str | None:
	row = _owned_community_row(user, ["name"])
	return row.name if row else None


def community_draft(user: str) -> CommunityDraft | None:
	row = _owned_community_row(user, ["name", "team_name", "slug", "logo", "short_description"])
	return CommunityDraft(**row) if row else None


def save_community(
	user: str, team_name: str, slug: str, logo: str | None, short_description: str | None
) -> str:
	ensure_communities_enabled()
	team = owned_community(user) or create_community(team_name, slug).team
	doc = frappe.get_doc("Buzz Team", team)
	public_page.set_slug(doc, slug)
	doc.update({"team_name": team_name, "logo": logo, "short_description": short_description})
	doc.save(ignore_permissions=True)
	return doc.name
