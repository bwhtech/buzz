from typing import TYPE_CHECKING

import frappe

from buzz.api.sponsorships.exceptions import (
	EnquiryAlreadyPaid,
	EnquiryAlreadyWithdrawn,
	EnquiryLogoLocked,
	LogoChangeNotPermitted,
	PaymentNotPermitted,
	WithdrawalNotPermitted,
)
from buzz.api.sponsorships.schemas import SponsorshipListItem
from buzz.events.doctype.event_venue.event_venue import set_venue_names
from buzz.payments import get_payment_link_for_sponsorship

if TYPE_CHECKING:
	from buzz.proposals.doctype.sponsorship_enquiry.sponsorship_enquiry import SponsorshipEnquiry

# Settled outcomes: a payment or sponsor, a removed sponsor, or the applicant's withdrawal.
LOCKED_STATUSES = ("Paid", "Cancelled", "Withdrawn")


class SponsorshipService:
	"""Act on one Sponsorship Enquiry on behalf of its owner."""

	def __init__(self, enquiry_id: str):
		self.enquiry_id = enquiry_id

	@property
	def enquiry(self) -> "SponsorshipEnquiry":
		return frappe.get_cached_doc("Sponsorship Enquiry", self.enquiry_id)

	@property
	def is_owner(self) -> bool:
		return self.enquiry.is_applicant()

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

	def change_logo(self, company_logo: str) -> None:
		if not self.is_owner:
			LogoChangeNotPermitted.throw()
		enquiry = self.enquiry
		if enquiry.status in LOCKED_STATUSES:
			EnquiryLogoLocked.throw()

		enquiry.company_logo = company_logo
		enquiry.save(ignore_permissions=True)


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
