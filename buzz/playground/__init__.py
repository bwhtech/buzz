import frappe
from frappe.utils import cint, now_datetime, time_diff_in_hours


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
		"hours_left": expires_on and max(0, round(time_diff_in_hours(expires_on, now_datetime()))),
	}


def configure_site():
	"""Frappe stores rendered PDFs on the Email Queue as the sender, which a visitor cannot write to."""
	if is_playground():
		frappe.db.set_single_value("System Settings", "store_attached_pdf_document", 0)
