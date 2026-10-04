import frappe
from frappe import _

from buzz.api.events.exceptions import TaxDetailsMissing
from buzz.api.events.services import ensure_event_team_access, manageable_event
from buzz.api.teams.exceptions import CannotEditTeam
from buzz.permissions import can_manage_members


def team_tax_details(team: str) -> dict:
	legal_name, tax_id = frappe.db.get_value("Buzz Team Settings", team, ["legal_name", "tax_id"])
	return {"team_legal_name": legal_name, "team_tax_id": tax_id}


def update_tax_settings(
	event: str, apply_tax: bool, tax_inclusive: bool, tax_label: str, tax_percentage: float
) -> None:
	doc = manageable_event(event)
	if apply_tax and not team_tax_details(doc.team)["team_tax_id"]:
		TaxDetailsMissing.throw()
	doc.update(
		{
			"apply_tax": apply_tax,
			"tax_inclusive": tax_inclusive,
			"tax_label": tax_label,
			"tax_percentage": tax_percentage,
		}
	)
	doc.save()


def update_team_tax_details(event: str, legal_name: str, tax_id: str, billing_address: str) -> None:
	ensure_event_team_access(event)
	team = frappe.db.get_value("Buzz Event", event, "team")
	if not can_manage_members(team):
		CannotEditTeam.throw()
	# Empty details are valid on the team, but this endpoint exists to add them.
	if not tax_id.strip():
		frappe.throw(_("Enter your team's legal name, tax ID and billing address."))
	settings = frappe.get_doc("Buzz Team Settings", team)
	settings.update({"legal_name": legal_name, "tax_id": tax_id, "billing_address": billing_address})
	settings.save(ignore_permissions=True)
