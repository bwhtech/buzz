import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests import factories
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	BuzzTeamMembershipFactory,
	EventBookingFactory,
	EventTicketFactory,
	EventTicketTypeFactory,
	EventVenueFactory,
	SponsorshipTierFactory,
	TalkProposalFactory,
	UserFactory,
)


class TestFactoryDefaults(IntegrationTestCase):
	def test_every_factory_saves_with_its_defaults(self):
		for name in factories.__all__:
			factory = getattr(factories, name)
			with self.subTest(factory=factory.__name__):
				doc = factory.create()
				self.assertTrue(frappe.db.exists(factory.doctype, doc.name))

	def test_create_once_reuses_the_user(self):
		first = UserFactory.create_once("factory-create-once@example.com")
		second = UserFactory.create_once("factory-create-once@example.com")

		self.assertEqual(first.name, second.name)

	def test_owned_team_has_the_given_owner(self):
		owner = UserFactory.create_once("factory-team-owner-check@example.com").name
		team = BuzzTeamFactory.create_owned_by(owner)

		role = frappe.db.get_value("Buzz Team Membership", {"team": team.name, "user": owner}, "team_role")
		self.assertEqual(role, "Owner")

	def test_set_settings_writes_team_settings(self):
		team = BuzzTeamFactory.create_owned_by().name

		BuzzTeamFactory.set_settings(team, {"legal_name": "Factory Pvt Ltd"})

		self.assertEqual(frappe.get_cached_doc("Buzz Team Settings", team).legal_name, "Factory Pvt Ltd")


class TestEventFactoryTraits(IntegrationTestCase):
	def test_unpublished(self):
		self.assertEqual(BuzzEventFactory.create("unpublished").is_published, 0)

	def test_in_person_has_a_venue_on_the_event_team(self):
		event = BuzzEventFactory.create("in_person")

		self.assertEqual(event.medium, "In Person")
		self.assertEqual(frappe.db.get_value("Event Venue", event.venue, "team"), event.team)

	def test_in_person_keeps_a_given_venue(self):
		team = BuzzTeamFactory.create_owned_by().name
		venue = EventVenueFactory.create(team=team).name

		self.assertEqual(BuzzEventFactory.create("in_person", team=team, venue=venue).venue, venue)

	def test_with_tax(self):
		event = BuzzEventFactory.create("with_tax")

		self.assertEqual((event.apply_tax, event.tax_label, event.tax_percentage), (1, "GST", 18))


class TestTicketingFactoryTraits(IntegrationTestCase):
	def test_paid_ticket_type(self):
		ticket_type = EventTicketTypeFactory.create("paid")

		self.assertEqual([(row.currency, row.price) for row in ticket_type.prices], [("INR", 500)])

	def test_unpublished_ticket_type(self):
		self.assertEqual(EventTicketTypeFactory.create("unpublished").is_published, 0)

	def test_submitted_ticket(self):
		self.assertEqual(EventTicketFactory.create("submitted").docstatus, 1)

	def test_booking_attendee_uses_a_ticket_type_of_the_event(self):
		booking = EventBookingFactory.create()

		ticket_type_event = frappe.db.get_value(
			"Event Ticket Type", booking.attendees[0].ticket_type, "event"
		)
		self.assertEqual(ticket_type_event, str(booking.event))

	def test_membership_takes_a_role(self):
		self.assertEqual(BuzzTeamMembershipFactory.create(team_role="Viewer").team_role, "Viewer")


class TestProposalFactoryTraits(IntegrationTestCase):
	def test_guest_submitted_talk_proposal(self):
		self.assertEqual(TalkProposalFactory.create("guest_submitted").submitted_by, "Guest")

	def test_sponsorship_tier_has_an_inr_price(self):
		tier = SponsorshipTierFactory.create()

		self.assertEqual([row.currency for row in tier.prices], ["INR"])
