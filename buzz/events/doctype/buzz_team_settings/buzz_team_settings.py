# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

SEEDED_FIELDS = (
	"support_email",
	"allow_transfer_ticket_before_event_start_days",
	"allow_add_ons_change_before_event_start_days",
	"allow_ticket_cancellation_request_before_event_start_days",
	"default_ticket_email_template",
	"default_booking_confirmation_email_template",
	"auto_send_pitch_deck",
	"default_sponsor_deck_email_template",
	"default_sponsor_deck_reply_to",
	"default_sponsor_deck_cc",
)

# A custom field on both doctypes, so it only exists where zoom_integration is installed.
ZOOM_SEEDED_FIELD = "default_webinar_template"


def seeded_fields() -> tuple[str, ...]:
	if "zoom_integration" in frappe.get_installed_apps():
		return (*SEEDED_FIELDS, ZOOM_SEEDED_FIELD)
	return SEEDED_FIELDS


def create_team_settings(team: str) -> "BuzzTeamSettings":
	"""Copy the current globals into a team's own settings. Idempotent."""
	if frappe.db.exists("Buzz Team Settings", team):
		return frappe.get_doc("Buzz Team Settings", team)

	site_settings = frappe.get_cached_doc("Buzz Settings")
	values = {fieldname: site_settings.get(fieldname) for fieldname in seeded_fields()}
	return frappe.get_doc({"doctype": "Buzz Team Settings", "team": team, **values}).insert(
		ignore_permissions=True
	)


def get_team_settings(team: str) -> "BuzzTeamSettings":
	"""A missing row is a bug — team creation and the seed patch cover every path."""
	return frappe.get_cached_doc("Buzz Team Settings", team)


def get_event_team_settings(event: str | int) -> "BuzzTeamSettings":
	return get_team_settings(frappe.get_cached_value("Buzz Event", event, "team"))


TAX_DETAIL_FIELDS = ("legal_name", "tax_id", "billing_address")


class BuzzTeamSettings(Document):
	def validate(self):
		self.validate_tax_details()

	def validate_tax_details(self):
		"""Tax details are all or nothing: a tax ID alone cannot go on an invoice."""
		for fieldname in TAX_DETAIL_FIELDS:
			self.set(fieldname, (self.get(fieldname) or "").strip() or None)
		if self.tax_id:
			self.tax_id = self.tax_id.upper()
		elif self.tax_id_removed():
			self.legal_name = self.billing_address = None
		if any(self.get(fieldname) for fieldname in TAX_DETAIL_FIELDS) and not all(
			self.get(fieldname) for fieldname in TAX_DETAIL_FIELDS
		):
			frappe.throw(_("Legal Name, Tax ID and Billing Address must be filled in together."))

	def tax_id_removed(self) -> bool:
		previous = self.get_doc_before_save()
		return bool(previous and previous.tax_id and not self.tax_id)
