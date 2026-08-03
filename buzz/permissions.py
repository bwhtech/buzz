# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.query_builder import Criterion
from frappe.query_builder.builder import QueryBuilder

WRITE_ROLES = frozenset({"Owner", "Admin", "Manager"})
ADMIN_ROLES = frozenset({"Owner", "Admin"})
WRITE_PTYPES = frozenset({"write", "create", "submit", "cancel", "amend", "delete"})

# Attendees, sponsors and speakers reach their own rows without any membership.
OWNER_VISIBLE_DOCTYPES = frozenset({"Event Booking", "Event Ticket", "Sponsorship Enquiry", "Event Talk"})


def is_unrestricted(user: str) -> bool:
	return user == "Administrator" or "System Manager" in frappe.get_roles(user)


def my_teams(user: str) -> QueryBuilder:
	membership = frappe.qb.DocType("Buzz Team Membership")
	return (
		frappe.qb.from_(membership)
		.select(membership.team)
		.where((membership.user == user) & (membership.enabled == 1))
	)


def published_events() -> QueryBuilder:
	event = frappe.qb.DocType("Buzz Event")
	return frappe.qb.from_(event).select(event.name).where(event.is_published == 1)


def my_team_events(user: str) -> QueryBuilder:
	event = frappe.qb.DocType("Buzz Event")
	return frappe.qb.from_(event).select(event.name).where(event.team.isin(my_teams(user)))


def team_role_of(user: str, team: str | None) -> str | None:
	if not team:
		return None
	return frappe.db.get_value(
		"Buzz Team Membership", {"user": user, "team": team, "enabled": 1}, "team_role"
	)


def role_allows(team_role: str, ptype: str) -> bool:
	if ptype == "delete":
		return team_role in ADMIN_ROLES
	if ptype in WRITE_PTYPES:
		return team_role in WRITE_ROLES
	return True


def has_team_access(team: str | None, ptype: str, user: str) -> bool:
	"""Deny-only check for a document belonging to `team`."""
	if is_unrestricted(user):
		return True
	# An unstamped row predates the backfill; role permissions still gate it.
	if not team:
		return True

	team_role = team_role_of(user, team)
	return bool(team_role) and role_allows(team_role, ptype)


def team_query_conditions(user: str | None = None, doctype: str | None = None, **kwargs) -> Criterion | None:
	user = user or frappe.session.user
	if is_unrestricted(user):
		return None

	table = frappe.qb.DocType(doctype)
	if doctype == "Buzz Event":
		if user == "Guest":
			return None
		return table.team.isin(my_teams(user)) | (table.is_published == 1)

	return table.team.isin(my_teams(user))


def derived_query_conditions(
	user: str | None = None, doctype: str | None = None, **kwargs
) -> Criterion | None:
	user = user or frappe.session.user
	if is_unrestricted(user):
		return None

	table = frappe.qb.DocType(doctype)
	criterion = table.event.isin(my_team_events(user))
	if doctype in OWNER_VISIBLE_DOCTYPES:
		criterion |= table.owner == user
	if doctype == "Sponsorship Tier":
		criterion |= table.event.isin(published_events())

	return criterion


def team_doc_query_conditions(user: str | None = None, **kwargs) -> Criterion | None:
	user = user or frappe.session.user
	if is_unrestricted(user):
		return None
	return frappe.qb.DocType("Buzz Team").name.isin(my_teams(user))


def membership_query_conditions(user: str | None = None, **kwargs) -> Criterion | None:
	user = user or frappe.session.user
	if is_unrestricted(user):
		return None
	return frappe.qb.DocType("Buzz Team Membership").team.isin(my_teams(user))


def team_has_permission(doc, ptype: str = "read", user: str | None = None, **kwargs) -> bool:
	user = user or frappe.session.user
	if doc.doctype == "Buzz Event" and ptype not in WRITE_PTYPES and doc.is_published:
		return True
	return has_team_access(doc.team, ptype, user)


def derived_has_permission(doc, ptype: str = "read", user: str | None = None, **kwargs) -> bool:
	user = user or frappe.session.user
	if doc.doctype in OWNER_VISIBLE_DOCTYPES and doc.owner == user:
		return True
	if doc.doctype == "Sponsorship Tier" and ptype not in WRITE_PTYPES:
		if frappe.db.get_value("Buzz Event", doc.event, "is_published"):
			return True

	# These doctypes carry no team column, so the team comes from their event.
	team = frappe.db.get_value("Buzz Event", doc.event, "team") if doc.event else None
	return has_team_access(team, ptype, user)


def team_doc_has_permission(doc, ptype: str = "read", user: str | None = None, **kwargs) -> bool:
	user = user or frappe.session.user
	if is_unrestricted(user):
		return True

	team_role = team_role_of(user, doc.name)
	if not team_role:
		return doc.is_new()
	if ptype == "delete":
		return team_role == "Owner"
	if ptype in WRITE_PTYPES:
		return team_role in ADMIN_ROLES
	return True


def membership_has_permission(doc, ptype: str = "read", user: str | None = None, **kwargs) -> bool:
	user = user or frappe.session.user
	if is_unrestricted(user):
		return True

	team_role = team_role_of(user, doc.team)
	if not team_role:
		return False
	if ptype in WRITE_PTYPES:
		return team_role in ADMIN_ROLES
	return True
