# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.query_builder import Criterion

# Roles that reach every row on these doctypes. Buzz User reaches only its own, which is
# what the functions below work out; `if_owner` cannot, because it asks who created the row.
PRIVILEGED_ROLES = frozenset({"System Manager", "Event Manager"})

# The column naming who a row belongs to: a booking made on someone else's behalf, or a
# guest checkout running as Administrator, leaves `owner` naming neither buyer nor attendee.
IDENTITY_FIELDS = {"Event Booking": "user", "Event Ticket": "attendee_email"}


def is_unrestricted(user: str) -> bool:
	return user == "Administrator" or bool(PRIVILEGED_ROLES & set(frappe.get_roles(user)))


def my_bookings(user: str):
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


def owned_query_conditions(user: str | None = None, doctype: str | None = None, **kwargs) -> Criterion | None:
	user = user or frappe.session.user
	if is_unrestricted(user):
		return None

	table = frappe.qb.DocType(doctype)
	criterion = table.owner == user
	if identity_field := IDENTITY_FIELDS.get(doctype):
		criterion |= table[identity_field] == user
	if doctype == "Event Ticket":
		criterion |= table.booking.isin(my_bookings(user))

	return criterion


def owned_has_permission(doc, ptype: str = "read", user: str | None = None, **kwargs) -> bool:
	user = user or frappe.session.user
	return is_unrestricted(user) or belongs_to_user(doc, user)
