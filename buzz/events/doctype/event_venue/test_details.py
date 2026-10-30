from frappe.tests import IntegrationTestCase

from buzz.events.doctype.event_venue.details import venue_details
from buzz.tests.factories import BuzzTeamFactory, EventVenueFactory


class IntegrationTestVenueDetails(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.team = BuzzTeamFactory.create_owned_by().name

	def venue(self, venue_name: str, latitude: float, longitude: float) -> str:
		return EventVenueFactory.create(
			team=self.team, venue_name=venue_name, latitude=latitude, longitude=longitude
		).name

	def test_single_venue_lists_itself_as_its_only_location(self):
		details = venue_details(self.venue("Town Hall", 12.97, 77.59))

		self.assertFalse(details.has_multiple_locations)
		self.assertEqual([location.venue_name for location in details.locations], ["Town Hall"])
		self.assertEqual(details.locations[0].map_link, details.map_link)

	def test_group_lists_its_locations_in_order(self):
		brewpub = self.venue("Brewpub", 12.97, 77.64)
		hall = self.venue("Main Hall", 13.02, 77.57)
		group = EventVenueFactory.create(
			team=self.team,
			has_multiple_locations=1,
			locations=[{"venue": brewpub, "label": "After-party"}, {"venue": hall, "label": "Main stage"}],
		)

		details = venue_details(group.name)

		self.assertEqual(
			[(location.label, location.venue_name, location.latitude) for location in details.locations],
			[("After-party", "Brewpub", 12.97), ("Main stage", "Main Hall", 13.02)],
		)
		self.assertIsNone(details.map_link)
