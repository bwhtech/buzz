from typing import Any

from faker import Faker
from frappe.tests.classes.context_managers import set_user
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.proposals.doctype.talk_proposal.talk_proposal import TalkProposal

_fake = Faker()


class TalkProposalFactory(BaseFactory[TalkProposal]):
	"""`validate` fills an empty `submitted_by` with the session user."""

	doctype = "Talk Proposal"

	@classmethod
	def create_as_guest(cls, event: str, speaker_email: str, **overrides: Any) -> TalkProposal:
		"""The public form's submission: `owner` and `submitted_by` are both Guest."""
		speakers = [{"first_name": "Speaker", "email": speaker_email}]
		with set_user("Guest"):
			return cls.create(
				"guest_submitted",
				event=event,
				speakers=speakers,
				flags={"ignore_permissions": True},
				**overrides,
			)

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
		"""`insert` still sets `owner` to the session user."""
		return {"submitted_by": "Guest"}
