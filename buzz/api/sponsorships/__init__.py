import frappe

from buzz.api.sponsorships.schemas import SponsorshipDetailsResponse, SponsorshipListItem
from buzz.api.sponsorships.services import SponsorshipService, list_user_enquiries


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
