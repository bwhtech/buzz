import json

import frappe

from buzz.api.events.exceptions import CannotManageEvent
from buzz.api.sponsorships import get_event_sponsors, get_event_sponsorships
from buzz.api.tags import set_tags
from buzz.tests.base_test_cases import SponsorshipTestCase
from buzz.tests.factories import BuzzEventFactory, BuzzTagFactory, EventSponsorFactory


class TestSponsorList(SponsorshipTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.team = frappe.db.get_value("Buzz Event", cls.event, "team")

	def setUp(self):
		# Rollback is per class, so each test lists the sponsors of its own event.
		self.event = str(BuzzEventFactory.create(team=self.team).name)
		super().setUp()
		self.acme = self.make_sponsor().name
		self.globex = EventSponsorFactory.create(event=self.event, company_name="Globex").name
		self.vip = BuzzTagFactory.create(team=self.team)
		set_tags("Event Sponsor", self.acme, [self.vip.name])

	def sponsors(self, *triples, search=None) -> set[str]:
		response = get_event_sponsors(self.event, search=search, filters=json.dumps(triples))
		return {sponsor.name for sponsor in response.sponsors}

	def test_sponsor_lists_its_tags(self):
		response = get_event_sponsorships(self.event)

		sponsor = next(row for row in response.sponsors if row.name == self.acme)
		self.assertEqual([tag.name for tag in sponsor.tags], [self.vip.name])
		self.assertIn(self.vip.name, [tag.name for tag in response.tags])

	def test_filter_by_tag(self):
		self.assertEqual(self.sponsors(["tags", "in", [self.vip.name]]), {self.acme})
		self.assertEqual(self.sponsors(["tags", "not in", [self.vip.name]]), {self.globex})

	def test_filter_by_tier_and_search(self):
		self.assertEqual(self.sponsors(["tier", "in", [str(self.tier.name)]]), {self.acme})
		self.assertEqual(self.sponsors(search="glob"), {self.globex})

	def test_tag_filter_offers_only_sponsor_tags_of_the_team(self):
		event_tag = BuzzTagFactory.create(team=self.team, document_type="Buzz Event").name

		fields = {field.key: field for field in get_event_sponsors(self.event).filter_fields}
		offered = [option.value for option in fields["tags"].options]
		self.assertIn(self.vip.name, offered)
		self.assertNotIn(event_tag, offered)

	def test_non_member_is_refused(self):
		with self.set_user(self.make_stranger()), self.assertRaises(CannotManageEvent):
			get_event_sponsors(self.event)
