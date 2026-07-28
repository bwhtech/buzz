import frappe
from frappe import _

from buzz.utils import is_app_installed


@frappe.whitelist()
def get_campaign_details(campaign: str):
	if not frappe.db.exists("Buzz Campaign", campaign):
		frappe.throw(_("Campaign not found"), frappe.DoesNotExistError)

	campaign_doc = frappe.get_cached_doc("Buzz Campaign", campaign)

	if not campaign_doc.enabled:
		frappe.throw(_("This campaign is not active"))

	return {
		"title": campaign_doc.title,
		"description": campaign_doc.description,
		"event": campaign_doc.event,
	}


@frappe.whitelist()
def register_campaign_interest(campaign: str):
	if frappe.session.user == "Guest":
		frappe.throw(_("Please login to register your interest"))

	if not is_app_installed("crm"):
		frappe.throw(_("CRM integration is not available"))

	if not frappe.db.exists("Buzz Campaign", campaign):
		frappe.throw(_("Campaign not found"), frappe.DoesNotExistError)

	campaign_doc = frappe.get_cached_doc("Buzz Campaign", campaign)

	user = frappe.get_cached_doc("User", frappe.session.user)
	first_name = user.first_name or user.full_name or frappe.session.user.split("@")[0]

	existing_lead = frappe.db.exists(
		"CRM Lead",
		{"email": frappe.session.user, "buzz_campaign": campaign},
	)
	if existing_lead:
		frappe.throw(_("You have already registered for this campaign"))

	ticket = None
	if campaign_doc.event:
		ticket = frappe.db.get_value(
			"Event Ticket",
			{
				"attendee_email": frappe.session.user,
				"event": campaign_doc.event,
				"docstatus": 1,
			},
			"name",
		)

	lead = frappe.get_doc(
		{
			"doctype": "CRM Lead",
			"first_name": first_name,
			"email": frappe.session.user,
			"status": "New",
			"buzz_campaign": campaign,
			"event_ticket": ticket,
		}
	)
	lead.insert(ignore_permissions=True)
