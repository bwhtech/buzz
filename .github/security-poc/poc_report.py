"""Reads back what the PoC payloads actually persisted, and prints a verdict per vector.

The HTTP status alone does not settle anything here: `process_booking` inserts and
commits the booking before it ever reaches the payment gateway, so a payload can be
rejected at the response level and still have left a paid booking behind. This checks
the documents, not the response.

Copied into the app tree in CI and run with `bench execute buzz.poc_report.run`.
"""

import json
import os

import frappe

FIXTURE_PATH = "/home/runner/poc-fixture.json"
RESPONSES_PATH = "/home/runner/poc-responses.jsonl"

# vector -> (what the payload tried, what a fixed build must do)
VECTORS = {
	"price_manipulation": ("book a 500 add-on for 1", "charge the catalog price"),
	"free_meal": ("book a 500 add-on for 0", "charge the catalog price"),
	"honest_control": ("book with no price at all", "charge the catalog price"),
	"foreign_add_on": ("attach another event's add-on", "reject the booking"),
	"disabled_add_on": ("attach a disabled add-on", "reject the booking"),
	"invalid_option": ("send a value outside the options", "reject the booking"),
	"foreign_ticket_type": ("book another event's ticket type", "reject the booking"),
}
REJECT_VECTORS = {"foreign_add_on", "disabled_add_on", "invalid_option", "foreign_ticket_type"}


def load_responses() -> dict:
	responses = {}
	if not os.path.exists(RESPONSES_PATH):
		return responses

	with open(RESPONSES_PATH) as responses_file:
		for line in responses_file:
			line = line.strip()
			if line:
				record = json.loads(line)
				responses[record["vector"]] = record
	return responses


def find_booking(email: str) -> dict | None:
	attendees = frappe.get_all(
		"Event Booking Attendee",
		filters={"email": email, "parenttype": "Event Booking"},
		fields=["parent", "add_ons", "add_on_total", "amount"],
		parent="Event Booking",
		ignore_permissions=True,
	)
	if not attendees:
		return None

	attendee = attendees[0]
	booking = frappe.db.get_value(
		"Event Booking",
		attendee.parent,
		["name", "total_amount", "status", "payment_status", "docstatus"],
		as_dict=True,
	)

	stored_add_on_price = None
	if attendee.add_ons:
		add_on_rows = frappe.get_all(
			"Ticket Add-on Value",
			filters={"parent": attendee.add_ons, "parenttype": "Attendee Ticket Add-on"},
			fields=["add_on", "value", "price"],
			parent="Attendee Ticket Add-on",
			ignore_permissions=True,
		)
		if add_on_rows:
			stored_add_on_price = add_on_rows[0].price

	return {
		"booking": booking,
		"add_on_total": attendee.add_on_total,
		"stored_add_on_price": stored_add_on_price,
	}


def judge(vector: str, result: dict | None, catalog_price: float) -> tuple[str, str]:
	"""Returns (verdict, evidence). VULNERABLE means the payload got what it asked for."""
	if vector in REJECT_VECTORS:
		if result is None:
			return "BLOCKED", "no booking created"
		return "VULNERABLE", f"booking {result['booking'].name} created anyway"

	if result is None:
		return "BLOCKED", "no booking created"

	booking = result["booking"]
	charged = result["stored_add_on_price"]
	evidence = (
		f"booking {booking.name}: add-on charged {charged}, "
		f"add_on_total {result['add_on_total']}, total {booking.total_amount}, "
		f"docstatus {booking.docstatus}"
	)

	if charged is None:
		return "INCONCLUSIVE", evidence
	if float(charged) == float(catalog_price):
		return "BLOCKED", evidence
	return "VULNERABLE", evidence


def run() -> None:
	frappe.set_user("Administrator")

	with open(FIXTURE_PATH) as fixture_file:
		fixture = json.load(fixture_file)

	catalog_price = fixture["add_on_price"]
	responses = load_responses()

	revision = os.environ.get("POC_REVISION", "unknown")
	label = os.environ.get("POC_LABEL", "")
	endpoint = os.environ.get("ENDPOINT", "")

	lines = [
		f"### `{revision}` {label}",
		"",
		f"Endpoint: `{endpoint}` &nbsp; Catalog add-on price: **{catalog_price}**",
		"",
		"| Vector | Payload tried | HTTP | Verdict | Evidence |",
		"| --- | --- | --- | --- | --- |",
	]

	print(f"\n{'=' * 78}\n{revision} {label}  ({endpoint})\n{'=' * 78}")

	for vector, (tried, _expected) in VECTORS.items():
		record = responses.get(vector, {})
		email = record.get("email", "")
		status = record.get("status", "-")
		result = find_booking(email) if email else None
		verdict, evidence = judge(vector, result, catalog_price)

		print(f"{verdict:14} {vector:22} HTTP {status:4} {evidence}")
		lines.append(f"| `{vector}` | {tried} | {status} | **{verdict}** | {evidence} |")

	summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
	if summary_path:
		with open(summary_path, "a") as summary_file:
			summary_file.write("\n".join(lines) + "\n\n")
