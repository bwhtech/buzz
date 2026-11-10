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
from buzz.events.doctype.event_venue.event_venue import set_venue_names
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
		return self.enquiry.is_applicant()

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

	def payment_link(
		self, tier_id: str, payment_gateway: str | None = None, currency: str | None = None
	) -> str:
		if not self.is_owner:
			PaymentNotPermitted.throw()

		return get_payment_link_for_sponsorship(
			self.enquiry_id,
			tier_id,
			f"/b/manage/sponsorship?enquiry={self.enquiry_id}&success=true",
			payment_gateway=payment_gateway,
			currency=currency,
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
			venue=event.get_venue_name(),
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


# The columns behind one sponsor-side card. The event ones come over a link hop, so a
# deleted event leaves them empty.
USER_ENQUIRY_FIELDS = [
	"name",
	"company_name",
	"company_logo",
	"event",
	"event.title as event_title",
	"event.start_date",
	"event.start_time",
	"event.end_date",
	"event.venue as venue",
	"event.banner_image",
	"tier",
	"status",
	"creation",
]


def list_user_enquiries() -> list[SponsorshipListItem]:
	if frappe.session.user == "Guest":
		return []
	enquiries = frappe.db.get_all(
		"Sponsorship Enquiry",
		filters={"owner": frappe.session.user},
		fields=USER_ENQUIRY_FIELDS,
		order_by="creation desc",
	)
	set_venue_names(enquiries)
	tiers = tiers_by_name({enquiry.tier for enquiry in enquiries if enquiry.tier})
	sponsors = get_sponsors_by_enquiry([enquiry.name for enquiry in enquiries])
	return [
		user_enquiry_item(enquiry, tiers.get(str(enquiry.tier)), sponsors.get(enquiry.name))
		for enquiry in enquiries
	]


def user_enquiry_item(enquiry, tier, sponsor) -> SponsorshipListItem:
	# Once confirmed, the logo the event shows is the sponsor's, not the enquiry's.
	logo = sponsor.company_logo if sponsor and sponsor.company_logo else enquiry.company_logo
	return SponsorshipListItem(
		**{**enquiry, "company_logo": logo},
		tier_title=(tier.title if tier else enquiry.tier) or "",
		tier_price=tier.prices[0].price if tier and tier.prices else None,
		tier_currency=tier.prices[0].currency if tier and tier.prices else None,
		sponsor=sponsor.name if sponsor else None,
		has_sponsor=bool(sponsor),
	)


def get_sponsors_by_enquiry(enquiry_ids: list[str]) -> dict:
	if not enquiry_ids:
		return {}

	sponsors = frappe.db.get_all(
		"Event Sponsor", filters={"enquiry": ["in", enquiry_ids]}, fields=["name", "enquiry", "company_logo"]
	)
	return {sponsor.enquiry: sponsor for sponsor in sponsors}


def get_tier_title(tier: str) -> str:
	return frappe.db.get_value("Sponsorship Tier", tier, "title") or tier


def tiers_by_name(names: set[str]) -> dict:
	if not names:
		return {}
	rows = frappe.get_all(
		"Sponsorship Tier",
		filters={"name": ["in", list(names)]},
		fields=["name", "title", {"prices": ["currency", "price"]}],
		ignore_permissions=True,
	)
	# Link values arrive as strings even where the tier autonames to an integer.
	return {str(row.name): row for row in rows}
