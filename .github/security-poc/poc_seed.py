"""Seeds the fixtures the booking PoC needs, and writes their IDs out as JSON.

Copied into the app tree in CI and run with `bench execute buzz.poc_seed.run`, so it
works against any checked-out revision of buzz. The schema moved between the revisions
under test — `Buzz Team` only exists after the multi-tenancy change — so every
version-specific field is set only where the meta actually has it.
"""

import json

import frappe

ADD_ON_PRICE = 500
FIXTURE_PATH = "/home/runner/poc-fixture.json"


def has_field(doctype: str, fieldname: str) -> bool:
	return fieldname in {df.fieldname for df in frappe.get_meta(doctype).fields}


def ensure_prompt_named(doctype: str, record_name: str) -> str:
	if not frappe.db.exists(doctype, record_name):
		doc = frappe.new_doc(doctype)
		doc.name = record_name
		doc.insert(ignore_permissions=True)
	return record_name


def ensure_team(team_name: str) -> str | None:
	"""Only the post-multi-tenancy revisions have teams; earlier ones must not get one."""
	if not frappe.db.exists("DocType", "Buzz Team") or not has_field("Buzz Event", "team"):
		return None

	existing = frappe.db.get_value("Buzz Team", {"team_name": team_name}, "name")
	if existing:
		return existing

	team = frappe.new_doc("Buzz Team")
	team.team_name = team_name
	team.insert(ignore_permissions=True)
	return team.name


def create_event(title: str, category: str, host: str, team: str | None) -> str:
	event = frappe.new_doc("Buzz Event")
	event.title = title
	event.category = category
	event.host = host
	event.start_date = "2030-01-01"
	event.end_date = "2030-01-01"
	event.start_time = "10:00:00"
	event.end_time = "18:00:00"
	event.medium = "Online"
	event.is_published = 1
	if team:
		event.team = team
	event.insert(ignore_permissions=True)
	return str(event.name)


def create_free_ticket_type(event: str, title: str) -> str:
	ticket_type = frappe.new_doc("Event Ticket Type")
	ticket_type.event = event
	ticket_type.title = title
	ticket_type.price = 0
	ticket_type.currency = "INR"
	ticket_type.is_published = 1
	ticket_type.insert(ignore_permissions=True)
	return str(ticket_type.name)


def create_add_on(event: str, title: str, enabled: int = 1, with_options: int = 1) -> str:
	add_on = frappe.new_doc("Ticket Add-on")
	add_on.event = event
	add_on.title = title
	add_on.price = ADD_ON_PRICE
	add_on.currency = "INR"
	add_on.enabled = enabled
	if with_options:
		add_on.user_selects_option = 1
		add_on.options = "Vegetarian meal\nNon-veg meal"
	add_on.insert(ignore_permissions=True)
	return str(add_on.name)


def run() -> None:
	frappe.set_user("Administrator")

	category = ensure_prompt_named("Event Category", "PoC Conference")
	host = ensure_prompt_named("Event Host", "PoC Host")

	target_team = ensure_team("PoC Target Team")
	foreign_team = ensure_team("PoC Foreign Team")

	target_event = create_event("PoC Target Event", category, host, target_team)
	foreign_event = create_event("PoC Foreign Event", category, host, foreign_team)

	fixture = {
		"add_on_price": ADD_ON_PRICE,
		"event": target_event,
		"ticket_type": create_free_ticket_type(target_event, "PoC Free Ticket"),
		"add_on": create_add_on(target_event, "PoC Meal"),
		"disabled_add_on": create_add_on(target_event, "PoC Disabled Meal", enabled=0),
		"foreign_event": foreign_event,
		"foreign_add_on": create_add_on(foreign_event, "PoC Foreign Meal"),
		"foreign_ticket_type": create_free_ticket_type(foreign_event, "PoC Foreign Ticket"),
	}

	frappe.db.commit()  # nosemgrep: frappe-semgrep-rules.rules.frappe-manual-commit

	with open(FIXTURE_PATH, "w") as fixture_file:
		json.dump(fixture, fixture_file, indent=2)

	print(json.dumps(fixture, indent=2))
