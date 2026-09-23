import frappe

from buzz.api.forms.schemas import CustomFormResponse
from buzz.api.sponsorships.enquiries import (
	ENQUIRIES_PAGE_SIZE,
	enquiry_detail,
	event_enquiries,
	set_enquiry_status,
)
from buzz.api.sponsorships.forms import SponsorFormService
from buzz.api.sponsorships.manage import event_sponsorships
from buzz.api.sponsorships.schemas import (
	EnquiryDetail,
	EventEnquiriesResponse,
	EventSponsorshipsResponse,
	SponsorshipDetailsResponse,
	SponsorshipListItem,
)
from buzz.api.sponsorships.services import SponsorshipService, list_user_enquiries


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_enquiry_form(event_route: str, form_route: str = "enquire-sponsorship") -> CustomFormResponse:
	return SponsorFormService(event_route, form_route).form_data()


# nosemgrep: guest-whitelisted-method
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


@frappe.whitelist(methods=["GET"])
def get_event_sponsorships(event: str) -> EventSponsorshipsResponse:
	return event_sponsorships(event)


@frappe.whitelist(methods=["GET"])
def get_event_sponsorship_enquiries(
	event: str,
	search: str | None = None,
	statuses: str | None = None,
	order: str = "desc",
	start: int = 0,
	limit: int = ENQUIRIES_PAGE_SIZE,
) -> EventEnquiriesResponse:
	"""`statuses` is comma-joined, the same string the dashboard keeps the filter in."""
	return event_enquiries(event, search, statuses, order, start, limit)


@frappe.whitelist(methods=["GET"])
def get_event_sponsorship_enquiry(enquiry: str) -> EnquiryDetail:
	return enquiry_detail(enquiry)


@frappe.whitelist(methods=["POST"])
def update_enquiry_status(enquiry: str, status: str) -> str:
	return set_enquiry_status(enquiry, status)
