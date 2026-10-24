import frappe

from buzz.api.listings.document import openapi_document
from buzz.api.listings.schemas import EventListing
from buzz.api.listings.services import PartnerListings


@frappe.whitelist(methods=["POST"])
def upsert_event(event: EventListing) -> None:
	PartnerListings().upsert(event)


@frappe.whitelist(methods=["POST"])
def remove_event(source_id: str) -> None:
	PartnerListings().remove(source_id)


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True)
def openapi() -> dict:
	return openapi_document()
