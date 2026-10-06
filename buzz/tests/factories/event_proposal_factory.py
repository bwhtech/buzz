from typing import Any

from faker import Faker
from frappe.utils import add_days, today
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.proposals.doctype.event_proposal.event_proposal import EventProposal

_fake = Faker()


class EventProposalFactory(BaseFactory[EventProposal]):
	"""An online one-day proposal with no host. `validate` refuses a start date in the past."""

	doctype = "Event Proposal"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import EventCategoryFactory

		return {
			"title": f"Proposal {_fake.catch_phrase()}",
			"category": self.overrides.get("category") or EventCategoryFactory.create().name,
			"medium": "Online",
			"start_date": add_days(today(), 30),
			"start_time": "10:00:00",
			"end_time": "18:00:00",
			"about": f"<p>{_fake.paragraph()}</p>",
		}

	@property
	def approved(self) -> dict[str, Any]:
		return {"status": "Approved"}
