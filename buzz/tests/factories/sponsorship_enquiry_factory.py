from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.proposals.doctype.sponsorship_enquiry.sponsorship_enquiry import SponsorshipEnquiry

_fake = Faker()


class SponsorshipEnquiryFactory(BaseFactory[SponsorshipEnquiry]):
	"""Entered by the team, so no enquiry form and no contact email is needed."""

	doctype = "Sponsorship Enquiry"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzEventFactory

		return {
			"event": self.overrides.get("event") or BuzzEventFactory.create().name,
			"company_name": _fake.company(),
			"company_logo": "/files/logo.png",
		}
