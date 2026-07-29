import frappe
from frappe import _

from buzz.api.campaigns.exceptions import AlreadyRegistered, CampaignNotActive, CRMNotAvailable
from buzz.api.campaigns.schemas import CampaignResponse
from buzz.utils import is_app_installed


@frappe.whitelist()
def get_campaign_details(campaign: str) -> CampaignResponse:
	campaign_doc = get_campaign(campaign)

	if not campaign_doc.enabled:
		CampaignNotActive.throw()

	return CampaignResponse(
		title=campaign_doc.title,
		description=campaign_doc.description,
		event=campaign_doc.event,
	)


@frappe.whitelist()
def register_campaign_interest(campaign: str) -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Please login to register your interest"), frappe.AuthenticationError)

	if not is_app_installed("crm"):
		CRMNotAvailable.throw()

	campaign_doc = get_campaign(campaign)

	if frappe.db.exists("CRM Lead", {"email": frappe.session.user, "buzz_campaign": campaign}):
		AlreadyRegistered.throw()

	create_campaign_lead(campaign_doc)


def get_campaign(campaign: str):
	if not frappe.db.exists("Buzz Campaign", campaign):
		frappe.throw(_("Campaign not found"), frappe.DoesNotExistError)

	return frappe.get_cached_doc("Buzz Campaign", campaign)


def create_campaign_lead(campaign_doc) -> None:
	user = frappe.get_cached_doc("User", frappe.session.user)
	first_name = user.first_name or user.full_name or frappe.session.user.split("@")[0]

	lead = frappe.get_doc(
		{
			"doctype": "CRM Lead",
			"first_name": first_name,
			"email": frappe.session.user,
			"status": "New",
			"buzz_campaign": campaign_doc.name,
			"event_ticket": get_attendee_ticket(campaign_doc.event),
		}
	)
	lead.insert(ignore_permissions=True)


def get_attendee_ticket(event: str | None) -> str | None:
	if not event:
		return None

	return frappe.db.get_value(
		"Event Ticket",
		{"attendee_email": frappe.session.user, "event": event, "docstatus": 1},
		"name",
	)
