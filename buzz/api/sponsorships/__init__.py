import frappe

from buzz.api.forms.schemas import CustomFormResponse
from buzz.api.sponsorships.forms import SponsorFormService
from buzz.api.sponsorships.schemas import SponsorshipDetailsResponse, SponsorshipListItem
from buzz.api.sponsorships.services import SponsorshipService, list_user_enquiries


# nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_enquiry_form(event_route: str, form_route: str = "enquire-sponsorship") -> CustomFormResponse:
	return SponsorFormService(event_route, form_route).form_data()


# nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
def submit_enquiry_form(
	event_route: str,
	data: dict | str,
	form_route: str = "enquire-sponsorship",
	custom_fields_data: dict | str | None = None,
) -> str:
	return SponsorFormService(event_route, form_route).submit(data, custom_fields_data)


@frappe.whitelist()
def get_sponsorship_details(enquiry_id: str) -> SponsorshipDetailsResponse:
	return SponsorshipService(enquiry_id).details()


@frappe.whitelist()
def get_user_sponsorship_inquiries() -> list[SponsorshipListItem]:
	return list_user_enquiries()


@frappe.whitelist()
def create_sponsorship_payment_link(enquiry_id: str, tier_id: str, payment_gateway: str | None = None) -> str:
	return SponsorshipService(enquiry_id).payment_link(tier_id, payment_gateway)


@frappe.whitelist()
def withdraw_sponsorship_enquiry(enquiry_id: str) -> None:
	SponsorshipService(enquiry_id).withdraw()
