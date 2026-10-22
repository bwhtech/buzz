from typing import TYPE_CHECKING

import frappe
from frappe.utils import add_to_date, now_datetime, time_diff_in_seconds

from buzz.analytics import capture, persona_of
from buzz.api.playground.exceptions import NotInSandbox, PlaygroundDisabled, UnknownPersona
from buzz.api.playground.schemas import ChecklistGroup, InboxAttachment, InboxEmail, RedirectResponse
from buzz.events.doctype.buzz_team.buzz_team import create_default_team_for
from buzz.events.doctype.buzz_team_membership.buzz_team_membership import upsert_membership
from buzz.playground import configure_site, is_playground, main_event, sandbox_of
from buzz.playground.checklist import PlaygroundChecklist
from buzz.playground.cleanup import delete_sandbox
from buzz.playground.demo_data import DemoData

if TYPE_CHECKING:
	from buzz.playground.doctype.playground_sandbox.playground_sandbox import PlaygroundSandbox

SANDBOX_HOURS = 24
PERSONAS = {
	"organizer": ("Alex", "Organizer"),
	"attendee": ("Sam", "Attendee"),
	"front_desk": ("Jordan", "Desk"),
}


def start() -> RedirectResponse:
	require_playground()
	configure_site()
	sandbox = create_sandbox()
	capture("playground_started", sandbox.name, {"sandbox": sandbox.name, "persona": "organizer"})
	return log_in(sandbox, "organizer")


def reset() -> RedirectResponse:
	sandbox = require_sandbox()
	old_sandbox = sandbox.name
	age_minutes = round(time_diff_in_seconds(now_datetime(), sandbox.creation) / 60)
	capture("playground_reset", old_sandbox, visitor_properties(sandbox, sandbox_age_minutes=age_minutes))
	# Log in first: deleting the session's own user clears the login cookies.
	response = start()
	delete_sandbox(old_sandbox)
	return response


def switch_persona(persona: str, redirect_to: str | None = None) -> RedirectResponse:
	if persona not in PERSONAS:
		UnknownPersona.throw(persona=persona)
	sandbox = require_sandbox()
	capture("persona_switched", sandbox.name, visitor_properties(sandbox, to_persona=persona))
	response = log_in(sandbox, persona)
	# Same-site paths only, so the endpoint never redirects off the playground.
	if redirect_to and redirect_to.startswith("/") and not redirect_to.startswith(("//", "/\\")):
		response.redirect_to = redirect_to
	return response


def visitor_properties(sandbox: "PlaygroundSandbox", **extra) -> dict:
	return {"sandbox": sandbox.name, "persona": persona_of(sandbox.name, frappe.session.user), **extra}


def get_checklist() -> list[ChecklistGroup]:
	return [ChecklistGroup(**group) for group in PlaygroundChecklist(require_sandbox()).groups()]


def create_sandbox() -> "PlaygroundSandbox":
	token = frappe.generate_hash(length=8)
	users = {persona: create_user(*names, token) for persona, names in PERSONAS.items()}
	team = create_default_team_for(users["organizer"]).name
	upsert_membership(team, users["front_desk"], "Frontdesk")
	DemoData(team, users["organizer"], users["attendee"]).create()
	expires_on = add_to_date(now_datetime(), hours=SANDBOX_HOURS)
	sandbox = frappe.get_doc(
		{"doctype": "Playground Sandbox", "team": team, "expires_on": expires_on, **users}
	)
	return sandbox.insert(ignore_permissions=True)


def create_user(first_name: str, last_name: str, token: str) -> str:
	user = frappe.get_doc(
		{
			"doctype": "User",
			# example.com never accepts mail, should a captured address ever leak out.
			"email": f"{first_name.lower()}-{token}@example.com",
			"first_name": first_name,
			"last_name": last_name,
			"send_welcome_email": 0,
			"roles": [{"role": "Buzz User"}],
		}
	)
	return user.insert(ignore_permissions=True).name


def log_in(sandbox: "PlaygroundSandbox", persona: str) -> RedirectResponse:
	frappe.local.login_manager.login_as(sandbox.get(persona))
	return RedirectResponse(redirect_to=landing_page(sandbox, persona))


def landing_page(sandbox: "PlaygroundSandbox", persona: str) -> str:
	if persona == "front_desk":
		return "/b/check-in"
	if persona == "attendee":
		event = main_event(sandbox)
		return f"/events/{event.route}" if event else "/events"
	return "/b/manage"


def require_playground():
	if not is_playground():
		PlaygroundDisabled.throw()


def require_sandbox() -> "PlaygroundSandbox":
	require_playground()
	name = sandbox_of(frappe.session.user)
	if not name:
		NotInSandbox.throw()
	return frappe.get_doc("Playground Sandbox", name)


def get_inbox() -> list[InboxEmail]:
	emails = frappe.get_all(
		"Playground Email",
		filters={"sandbox": require_sandbox().name},
		fields=["name", "subject", "sender", "recipient", "creation", "message"],
		order_by="creation desc",
		limit=100,
	)
	attachments = attachments_by_email([email.name for email in emails])
	return [
		InboxEmail(
			**{**email, "creation": str(email.creation), "attachments": attachments.get(email.name, [])}
		)
		for email in emails
	]


def attachments_by_email(emails: list[str]) -> dict[str, list[InboxAttachment]]:
	files = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Playground Email", "attached_to_name": ["in", emails]},
		fields=["name", "file_name", "attached_to_name"],
	)
	attachments = {}
	for file in files:
		attachment = InboxAttachment(name=file.name, file_name=file.file_name)
		attachments.setdefault(file.attached_to_name, []).append(attachment)
	return attachments


def download_attachment(file_name: str):
	sandbox = require_sandbox().name
	email = frappe.db.get_value(
		"File", {"name": file_name, "attached_to_doctype": "Playground Email"}, "attached_to_name"
	)
	if not email or frappe.db.get_value("Playground Email", email, "sandbox") != sandbox:
		NotInSandbox.throw()
	file = frappe.get_doc("File", file_name)
	frappe.local.response.update(
		{"type": "download", "filename": file.file_name, "filecontent": file.get_content()}
	)
