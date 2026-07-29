from typing import TYPE_CHECKING

import frappe

from buzz.api.sponsorships.exceptions import (
	EnquiryAlreadyPaid,
	EnquiryAlreadyWithdrawn,
	EnquiryNotAccessible,
	PaymentNotPermitted,
	WithdrawalNotPermitted,
)
from buzz.api.sponsorships.schemas import (
	EnquirySummary,
	EventSummary,
	SponsorshipDetailsResponse,
	SponsorshipListItem,
	SponsorSummary,
)
from buzz.payments import get_payment_link_for_sponsorship

if TYPE_CHECKING:
	from buzz.events.doctype.buzz_event.buzz_event import BuzzEvent
	from buzz.proposals.doctype.sponsorship_enquiry.sponsorship_enquiry import SponsorshipEnquiry


class SponsorshipService:
	"""Read and act on one Sponsorship Enquiry on behalf of its owner."""

	def __init__(self, enquiry_id: str):
		self.enquiry_id = enquiry_id

	@property
	def enquiry(self) -> "SponsorshipEnquiry":
		return frappe.get_cached_doc("Sponsorship Enquiry", self.enquiry_id)

	@property
	def event(self) -> "BuzzEvent":
		return frappe.get_cached_doc("Buzz Event", self.enquiry.event)

	@property
	def is_owner(self) -> bool:
		return self.enquiry.owner == frappe.session.user

	def details(self) -> SponsorshipDetailsResponse:
		if not self.is_owner and not frappe.has_permission("Sponsorship Enquiry", "read", self.enquiry):
			EnquiryNotAccessible.throw()

		sponsor = self.sponsor()
		return SponsorshipDetailsResponse(
			enquiry=self.enquiry_summary(),
			event_details=self.event_summary(),
			sponsor_details=sponsor,
			has_sponsor=bool(sponsor),
		)

	def payment_link(self, tier_id: str, payment_gateway: str | None = None) -> str:
		if not self.is_owner:
			PaymentNotPermitted.throw()

		return get_payment_link_for_sponsorship(
			self.enquiry_id,
			tier_id,
			f"/b/account/sponsorships/{self.enquiry_id}?success=true",
			payment_gateway=payment_gateway,
		)

	def withdraw(self) -> None:
		if not self.is_owner:
			WithdrawalNotPermitted.throw()

		enquiry = self.enquiry
		if enquiry.status == "Paid":
			EnquiryAlreadyPaid.throw()
		if enquiry.status == "Withdrawn":
			EnquiryAlreadyWithdrawn.throw()

		enquiry.status = "Withdrawn"
		enquiry.save(ignore_permissions=True)

	def enquiry_summary(self) -> EnquirySummary:
		enquiry = self.enquiry
		return EnquirySummary(
			name=enquiry.name,
			company_name=enquiry.company_name,
			company_logo=enquiry.company_logo,
			event=enquiry.event,
			tier=enquiry.tier,
			tier_title=get_tier_title(enquiry.tier) if enquiry.tier else "",
			status=enquiry.status,
			creation=enquiry.creation,
			owner=enquiry.owner,
		)

	def event_summary(self) -> EventSummary:
		event = self.event
		return EventSummary(
			title=event.title,
			short_description=event.short_description,
			about=event.about,
			start_date=event.start_date,
			end_date=event.end_date,
			venue=event.venue,
			route=event.route,
		)

	def sponsor(self) -> SponsorSummary | None:
		sponsors = frappe.db.get_all(
			"Event Sponsor",
			filters={"enquiry": self.enquiry_id},
			fields=["name", "company_name", "company_logo", "creation", "event", "tier"],
			limit=1,
		)
		if not sponsors:
			return None

		return SponsorSummary(**sponsors[0], tier_title=get_tier_title(sponsors[0].tier))


def list_user_enquiries() -> list[SponsorshipListItem]:
	enquiries = frappe.db.get_all(
		"Sponsorship Enquiry",
		filters={"owner": frappe.session.user},
		fields=["name", "company_name", "event", "tier", "status", "creation"],
		order_by="creation desc",
	)
	event_titles = get_titles("Buzz Event", {enquiry.event for enquiry in enquiries if enquiry.event})
	tier_titles = get_titles("Sponsorship Tier", {enquiry.tier for enquiry in enquiries if enquiry.tier})
	sponsored = get_sponsored_enquiries([enquiry.name for enquiry in enquiries])

	return [
		SponsorshipListItem(
			**enquiry,
			event_title=event_titles.get(enquiry.event),
			tier_title=(tier_titles.get(enquiry.tier) or enquiry.tier) if enquiry.tier else "",
			has_sponsor=enquiry.name in sponsored,
		)
		for enquiry in enquiries
	]


def get_titles(doctype: str, names: set[str]) -> dict[str, str]:
	if not names:
		return {}

	rows = frappe.get_all(doctype, filters={"name": ["in", list(names)]}, fields=["name", "title"])
	# Link fields arrive as strings even where the target autonames to an integer.
	return {str(row.name): row.title for row in rows}


def get_sponsored_enquiries(enquiry_ids: list[str]) -> set[str]:
	if not enquiry_ids:
		return set()

	sponsors = frappe.db.get_all(
		"Event Sponsor", filters={"enquiry": ["in", enquiry_ids]}, fields=["enquiry"]
	)
	return {sponsor.enquiry for sponsor in sponsors}


def get_tier_title(tier: str) -> str:
	return frappe.db.get_value("Sponsorship Tier", tier, "title") or tier
