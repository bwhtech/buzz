# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.query_builder import Criterion
from frappe.query_builder.builder import QueryBuilder

WRITE_ROLES = frozenset({"Owner", "Admin", "Manager"})
ADMIN_ROLES = frozenset({"Owner", "Admin"})
CHECKIN_ROLES = frozenset({"Owner", "Admin", "Manager", "Frontdesk"})
WRITE_PTYPES = frozenset({"write", "create", "submit", "cancel", "amend", "delete"})

SECTIONS = ("details", "guests", "ticketing", "talks", "sponsors", "communications")
EDIT = "Edit"
VIEW = "View"

DOCTYPE_SECTION = {
	"Buzz Event": "details",
	"Additional Event Page": "details",
	"Event Booking": "guests",
	"Event Ticket": "guests",
	"Event Check In": "guests",
	"Event Feedback": "guests",
	"Event Ticket Type": "ticketing",
	"Event Ticket Category": "ticketing",
	"Ticket Add-on": "ticketing",
	"Buzz Coupon Code": "ticketing",
	"Ticket Hold": "ticketing",
	"Offline Payment Method": "ticketing",
	"Buzz Custom Field": "ticketing",
	"Event Talk": "talks",
	"Talk Proposal": "talks",
	"Event Track": "talks",
	"Event Sponsor": "sponsors",
	"Sponsorship Tier": "sponsors",
	"Sponsorship Enquiry": "sponsors",
	"Sponsor Enquiry Form": "sponsors",
	"Event Communication": "communications",
}

# Attendees, sponsors and speakers reach their own rows without any membership.
OWNER_VISIBLE_DOCTYPES = frozenset({"Event Booking", "Event Ticket", "Sponsorship Enquiry", "Event Talk"})

# The column naming who a row belongs to: a booking made on someone else's behalf, or a
# guest checkout running as Administrator, leaves `owner` naming neither buyer nor attendee.
IDENTITY_FIELDS = {"Event Booking": "user", "Event Ticket": "attendee_email"}


def is_unrestricted(user: str) -> bool:
	return user == "Administrator" or "System Manager" in frappe.get_roles(user)


def as_sql(criterion: Criterion | None) -> str | None:
	"""Render a criterion the way the query engine itself does.

	A permission query hook hands back SQL text: whatever it returns is stringified,
	and pypika defaults to ANSI double quotes, which MariaDB reads as string literals.
	"""
	if criterion is None:
		return None
	quote_char = "`" if frappe.db.db_type == "mariadb" else '"'
	return criterion.get_sql(with_namespace=True, quote_char=quote_char)


def my_teams(user: str) -> QueryBuilder:
	membership = frappe.qb.DocType("Buzz Team Membership")
	return (
		frappe.qb.from_(membership)
		.select(membership.team)
		.where((membership.user == user) & (membership.enabled == 1))
	)


def my_team_names(user: str) -> list[str]:
	return frappe.get_all("Buzz Team Membership", filters={"user": user, "enabled": 1}, pluck="team")


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def team_link_query(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict | None
) -> list[tuple]:
	"""Link fields offer the user's own teams only.

	Narrower than the read permission on purpose: a System Manager reads every team for
	support, but stamping a document with a team they are not on is never intended.
	"""
	pattern = f"%{txt}%"
	return frappe.get_all(
		"Buzz Team",
		filters={**(filters or {}), "name": ("in", my_team_names(frappe.session.user))},
		or_filters=[["name", "like", pattern], ["team_name", "like", pattern]],
		fields=["name", "team_name"],
		order_by="team_name asc",
		limit_start=start,
		limit_page_length=page_len,
		as_list=True,
	)


def published_events() -> QueryBuilder:
	event = frappe.qb.DocType("Buzz Event")
	return frappe.qb.from_(event).select(event.name).where(event.is_published == 1)


def collaborator_events(user: str, section: str) -> QueryBuilder:
	collaborator = frappe.qb.DocType("Buzz Event Collaborator")
	return (
		frappe.qb.from_(collaborator)
		.select(collaborator.event)
		.where(
			(collaborator.user == user)
			& (collaborator.status == "Accepted")
			& collaborator[f"{section}_access"].isin([VIEW, EDIT])
		)
	)


def events_with_section_access(user: str, section: str) -> QueryBuilder:
	"""The team's events, plus the events a collaborator holds `section` on."""
	event = frappe.qb.DocType("Buzz Event")
	return (
		frappe.qb.from_(event)
		.select(event.name)
		.where(event.team.isin(my_teams(user)) | event.name.isin(collaborator_events(user, section)))
	)


def my_bookings(user: str) -> QueryBuilder:
	booking = frappe.qb.DocType("Event Booking")
	return (
		frappe.qb.from_(booking).select(booking.name).where((booking.user == user) | (booking.owner == user))
	)


def belongs_to_user(doc, user: str) -> bool:
	"""Whether `doc` names `user`, whether or not they are the one who created it."""
	if doc.owner == user:
		return True

	if (identity_field := IDENTITY_FIELDS.get(doc.doctype)) and doc.get(identity_field) == user:
		return True

	# A ticket also belongs to whoever booked it, who is often not its attendee.
	if doc.doctype == "Event Ticket" and doc.booking:
		booking = frappe.db.get_value("Event Booking", doc.booking, ["user", "owner"], as_dict=True)
		return bool(booking) and user in (booking.user, booking.owner)

	return False


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


def team_role_access(team_role: str) -> dict[str, str]:
	if team_role in WRITE_ROLES:
		return dict.fromkeys(SECTIONS, EDIT)
	if team_role == "Frontdesk":
		return {section: EDIT if section == "guests" else VIEW for section in SECTIONS}
	return dict.fromkeys(SECTIONS, VIEW)


def collaborator_access(user: str, event: str) -> dict[str, str | None]:
	row = frappe.db.get_value(
		"Buzz Event Collaborator",
		{"event": event, "user": user, "status": "Accepted"},
		[f"{section}_access" for section in SECTIONS],
		as_dict=True,
	)
	return {section: (row[f"{section}_access"] or None) if row else None for section in SECTIONS}


def get_section_access(user: str, event: str) -> dict[str, str | None]:
	"""Section -> "View" | "Edit" | None, for a team member and a collaborator alike."""
	if is_unrestricted(user):
		return dict.fromkeys(SECTIONS, EDIT)

	team_role = team_role_of(user, frappe.db.get_value("Buzz Event", event, "team"))
	return team_role_access(team_role) if team_role else collaborator_access(user, event)


def collaborator_allows(user: str, event: str, section: str, ptype: str) -> bool:
	level = collaborator_access(user, event)[section]
	if not level or ptype == "delete":
		return False
	return level == EDIT or ptype not in WRITE_PTYPES


def has_section_permission(event: str | None, section: str, ptype: str, user: str | None = None) -> bool:
	"""Deny-only check for a document of `event`'s `section`; team roles are unchanged."""
	user = user or frappe.session.user
	team = frappe.db.get_value("Buzz Event", event, "team") if event else None
	# An unstamped row predates the backfill; role permissions still gate it.
	if is_unrestricted(user) or not team:
		return True
	if team_role := team_role_of(user, team):
		return role_allows(team_role, ptype)
	return collaborator_allows(user, event, section, ptype)


def can_check_in(event: str, user: str) -> bool:
	"""Front-desk work on an event. Unlike has_section_permission, an unstamped event fails closed."""
	if is_unrestricted(user):
		return True
	if team_role := team_role_of(user, frappe.db.get_value("Buzz Event", event, "team")):
		return team_role in CHECKIN_ROLES
	return collaborator_allows(user, event, "guests", "write")


def team_query_conditions(user: str | None = None, doctype: str | None = None, **kwargs) -> str | None:
	user = user or frappe.session.user
	if is_unrestricted(user):
		return None

	table = frappe.qb.DocType(doctype)
	if doctype == "Buzz Event":
		if user == "Guest":
			return None
		return as_sql(
			table.name.isin(events_with_section_access(user, "details")) | (table.is_published == 1)
		)

	return as_sql(table.team.isin(my_teams(user)))


def derived_criterion(user: str, doctype: str | None) -> Criterion | None:
	if is_unrestricted(user):
		return None

	table = frappe.qb.DocType(doctype)
	criterion = table.event.isin(events_with_section_access(user, DOCTYPE_SECTION[doctype]))
	if doctype in OWNER_VISIBLE_DOCTYPES:
		criterion |= table.owner == user

		if identity_field := IDENTITY_FIELDS.get(doctype):
			criterion |= table[identity_field] == user

		if doctype == "Event Ticket":
			criterion |= table.booking.isin(my_bookings(user))
	if doctype == "Sponsorship Tier":
		criterion |= table.event.isin(published_events())

	return criterion


def derived_query_conditions(user: str | None = None, doctype: str | None = None, **kwargs) -> str | None:
	return as_sql(derived_criterion(user or frappe.session.user, doctype))


def team_doc_query_conditions(user: str | None = None, **kwargs) -> str | None:
	user = user or frappe.session.user
	if is_unrestricted(user):
		return None
	return as_sql(frappe.qb.DocType("Buzz Team").name.isin(my_teams(user)))


def membership_query_conditions(user: str | None = None, **kwargs) -> str | None:
	user = user or frappe.session.user
	if is_unrestricted(user):
		return None
	return as_sql(frappe.qb.DocType("Buzz Team Membership").team.isin(my_teams(user)))


def team_has_permission(doc, ptype: str = "read", user: str | None = None, **kwargs) -> bool:
	user = user or frappe.session.user
	if doc.doctype == "Buzz Event" and ptype not in WRITE_PTYPES and doc.is_published:
		return True
	if doc.doctype == "Buzz Event" and not doc.is_new():
		return has_section_permission(doc.name, "details", ptype, user)
	return has_team_access(doc.team, ptype, user)


def derived_has_permission(doc, ptype: str = "read", user: str | None = None, **kwargs) -> bool:
	user = user or frappe.session.user
	if doc.doctype in OWNER_VISIBLE_DOCTYPES and belongs_to_user(doc, user):
		return True
	if doc.doctype == "Sponsorship Tier" and ptype not in WRITE_PTYPES:
		if frappe.db.get_value("Buzz Event", doc.event, "is_published"):
			return True

	# These doctypes carry no team column, so the team comes from their event.
	team = frappe.db.get_value("Buzz Event", doc.event, "team") if doc.event else None
	if not team and doc.doctype in OWNER_VISIBLE_DOCTYPES:
		# `has_team_access` waves an unstamped row through for a half-migrated site. These
		# rows hold personal data, so they get no such pass — the checks above are the way in.
		return is_unrestricted(user)

	return has_section_permission(doc.event, DOCTYPE_SECTION[doc.doctype], ptype, user)


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


def can_manage_members(team: str, user: str | None = None) -> bool:
	"""The membership-write rule below, asked about a team rather than a document."""
	user = user or frappe.session.user
	return is_unrestricted(user) or team_role_of(user, team) in ADMIN_ROLES


def team_admin_has_permission(doc, ptype: str = "read", user: str | None = None, **kwargs) -> bool:
	"""Memberships and settings are team administration: members read, Owner/Admin write."""
	user = user or frappe.session.user
	if is_unrestricted(user):
		return True

	team_role = team_role_of(user, doc.team)
	if not team_role:
		return False
	if ptype in WRITE_PTYPES:
		return team_role in ADMIN_ROLES
	return True
