import frappe
from frappe.tests import IntegrationTestCase

from buzz.emails import email_event_header
from buzz.events.doctype.event_venue.details import venue_details
from buzz.events.doctype.event_venue.map_image import LocationsMapImage
from buzz.events.online_meeting import OnlineMeeting
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, EventVenueFactory
from buzz.utils import generate_ics_file


class IntegrationTestLocationsInEmails(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.team = BuzzTeamFactory.create_owned_by().name
		cairo = EventVenueFactory.create(team=cls.team, venue_name="Museum", latitude=30.0, longitude=31.2)
		dubai = EventVenueFactory.create(team=cls.team, venue_name="Hotel", latitude=25.2, longitude=55.3)
		cls.group = EventVenueFactory.create(
			team=cls.team,
			has_multiple_locations=1,
			locations=[{"venue": cairo.name, "label": "Cairo"}, {"venue": dubai.name, "label": "Dubai"}],
		).name
		cls.event = BuzzEventFactory.create(team=cls.team, medium="In Person", venue=cls.group)

	def test_header_carries_the_locations_and_the_link_that_opens_them(self):
		header = email_event_header(self.event)

		self.assertEqual([location.venue_name for location in header.locations], ["Museum", "Hotel"])
		self.assertTrue(header.locations_url.endswith(f"/events/{self.event.route}#locations"))
		self.assertTrue(header.locations_map_url.endswith(".png"))

	def test_map_image_is_rendered_once_per_set_of_pins(self):
		locations = venue_details(self.group).locations

		first = LocationsMapImage(self.group, locations).url()
		second = LocationsMapImage(self.group, locations).url()

		self.assertEqual(first, second)
		self.assertEqual(frappe.db.count("File", {"file_url": first}), 1)

	def test_locations_without_coordinates_have_no_map(self):
		locations = venue_details(self.group).locations
		for location in locations:
			location.latitude = location.longitude = None

		self.assertIsNone(LocationsMapImage(self.group, locations).url())

	def test_event_email_lists_the_locations(self):
		html = frappe.render_template(
			"buzz/templates/emails/message.html",
			{"title": "Update", "message": "Doors open at 9.", "event_doc": self.event},
			is_path=True,
		)

		self.assertIn("WHERE · 2 LOCATIONS", html)
		self.assertIn(f"/events/{self.event.route}#locations", html)

	def test_calendar_invite_names_every_location(self):
		invite = generate_ics_file(self.event, "guest@example.com", OnlineMeeting(self.event))

		self.assertIn("LOCATION:Cairo: Museum · Dubai: Hotel", invite)
		self.assertIn("1. Cairo: Museum", invite)
