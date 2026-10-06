from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.proposals.doctype.talk_proposal.talk_proposal import TalkProposal

_fake = Faker()


class TalkProposalFactory(BaseFactory[TalkProposal]):
	"""One speaker. `validate` sets `submitted_by` to the session user when it is empty."""

	doctype = "Talk Proposal"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import BuzzEventFactory

		return {
			"event": self.overrides.get("event") or BuzzEventFactory.create().name,
			"title": _fake.sentence(nb_words=4).rstrip("."),
			"speakers": [{"first_name": _fake.first_name(), "email": _fake.email()}],
		}

	@property
	def guest_submitted(self) -> dict[str, Any]:
		"""The public form's `submitted_by`. `insert` still sets `owner` to the session user."""
		return {"submitted_by": "Guest"}
