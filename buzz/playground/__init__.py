import frappe
from frappe.utils import cint, now_datetime, time_diff_in_hours, today


def is_playground() -> bool:
	"""On only when the site sets `buzz_playground` and mutes email, so a sandbox never mails anyone."""
	return bool(frappe.conf.get("buzz_playground")) and bool(cint(frappe.conf.get("mute_emails")))


def sandbox_of(user: str) -> str | None:
	sandboxes = frappe.get_all(
		"Playground Sandbox",
		or_filters={"organizer": user, "attendee": user, "front_desk": user},
		pluck="name",
		limit=1,
	)
	return sandboxes[0] if sandboxes else None


def playground_boot() -> dict | None:
	if not is_playground():
		return None
	sandbox = sandbox_of(frappe.session.user)
	expires_on = sandbox and frappe.db.get_value("Playground Sandbox", sandbox, "expires_on")
	return {
		"signup_url": frappe.conf.get("buzz_playground_signup_url"),
		"sandbox": sandbox,
		"hours_left": expires_on and max(0, round(time_diff_in_hours(expires_on, now_datetime()))),
	}


def listing_filters() -> dict:
	"""Public listings on a playground show only the viewer's own sandbox, never other visitors'."""
	if not is_playground():
		return {}
	sandbox = sandbox_of(frappe.session.user)
	teams = sandbox_teams(frappe.get_doc("Playground Sandbox", sandbox)) if sandbox else []
	return {"team": ["in", teams or [""]]}


def add_noindex_header(response, request):
	if is_playground():
		response.headers["X-Robots-Tag"] = "noindex, nofollow"


def configure_site():
	"""Frappe stores rendered PDFs on the Email Queue as the sender, which a visitor cannot write to.

	Communities are on, so a visitor can create one from /community.
	"""
	if frappe.db.get_single_value("System Settings", "store_attached_pdf_document"):
		frappe.db.set_single_value("System Settings", "store_attached_pdf_document", 0)
	if not frappe.db.get_single_value("Buzz Settings", "enable_communities"):
		frappe.db.set_single_value("Buzz Settings", "enable_communities", 1)


def sandbox_teams(sandbox) -> list[str]:
	"""The seeded team plus every community the organizer created."""
	owned = frappe.get_all(
		"Buzz Team Membership", {"user": sandbox.organizer, "team_role": "Owner"}, pluck="team"
	)
	return list({sandbox.team, *owned})


def main_event(sandbox) -> dict | None:
	"""The seeded conference: the furthest upcoming event made before the visitor arrived."""
	return frappe.db.get_value(
		"Buzz Event",
		{"team": sandbox.team, "start_date": [">=", today()], "creation": ["<", sandbox.creation]},
		["name", "route", "title"],
		as_dict=True,
		order_by="start_date desc",
	)
