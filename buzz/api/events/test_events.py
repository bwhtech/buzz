import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.api.events import check_event_route, get_event, get_event_guests, get_my_events
from buzz.api.events import create_event as create_event_endpoint
from buzz.api.events.exceptions import (
	CannotCreateEvents,
	CannotManageEvent,
	EventNotFound,
	ZoomNotAvailable,
)
from buzz.api.events.schemas import NewEvent
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user, payload_for
from buzz.test_permissions import add_member, create_ticket
from buzz.utils import is_app_installed


def create_event(title: str, team: str, **overrides) -> str:
	payload = payload_for("Buzz Event", title) | {
		"start_date": add_days(today(), 30),
		"end_date": add_days(today(), 31),
	}
	event = frappe.get_doc({**payload, "team": team, **overrides}).insert(ignore_permissions=True)
	return str(event.name)


def issue_ticket(event: str, user: str) -> str:
	"""The booking flow submits every ticket it generates; the fixture stops at insert."""
	ticket = create_ticket(event, user)
	frappe.get_doc("Event Ticket", ticket).submit()
	return ticket


class TestGetMyEvents(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

		if not frappe.db.exists("Event Category", "Test Category"):
			frappe.get_doc({"doctype": "Event Category", "name": "Test Category"}).insert(
				ignore_permissions=True
			)
		if not frappe.db.exists("Event Host", "Test Host"):
			frappe.get_doc({"doctype": "Event Host", "name": "Test Host"}).insert(ignore_permissions=True)

		cls.host_user = create_user("events-host@example.com", "Host")
		cls.attendee = create_user("events-attendee@example.com", "Attendee")
		cls.host_team = create_owned_team("My Events Host Team", cls.host_user)
		cls.other_team = create_owned_team("My Events Other Team", cls.attendee)

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")

	def events_of(self, user: str) -> dict[str, list[dict]]:
		frappe.set_user(user)
		return get_my_events().__json__()

	def names_in(self, events: list[dict]) -> list[str]:
		return [event["name"] for event in events]

	def test_returns_unpublished_event_of_own_team_as_host(self):
		event = create_event("Own Draft", self.host_team, is_published=0)

		upcoming = self.events_of(self.host_user)["upcoming"]

		self.assertIn(event, self.names_in(upcoming))
		self.assertTrue(next(row for row in upcoming if row["name"] == event)["is_host"])

	def test_returns_ticketed_event_of_another_team_as_guest(self):
		event = create_event("Ticketed Elsewhere", self.host_team)
		issue_ticket(event, self.attendee)

		upcoming = self.events_of(self.attendee)["upcoming"]

		self.assertIn(event, self.names_in(upcoming))
		self.assertFalse(next(row for row in upcoming if row["name"] == event)["is_host"])

	def test_returns_hosted_and_ticketed_event_once_as_host(self):
		event = create_event("Hosting And Attending", self.host_team)
		issue_ticket(event, self.host_user)

		upcoming = self.events_of(self.host_user)["upcoming"]

		self.assertEqual(self.names_in(upcoming).count(event), 1)
		self.assertTrue(next(row for row in upcoming if row["name"] == event)["is_host"])

	def test_ignores_a_draft_ticket(self):
		event = create_event("Never Booked", self.other_team)
		create_ticket(event, self.host_user)

		events = self.events_of(self.host_user)

		self.assertNotIn(event, self.names_in(events["upcoming"] + events["past"]))

	def test_excludes_another_teams_event_without_a_ticket(self):
		event = create_event("Someone Elses", self.other_team, is_published=1)

		events = self.events_of(self.host_user)

		self.assertNotIn(event, self.names_in(events["upcoming"] + events["past"]))

	def test_keeps_an_event_in_progress_upcoming(self):
		event = create_event(
			"Still Running",
			self.host_team,
			start_date=add_days(today(), -1),
			end_date=add_days(today(), 1),
		)

		events = self.events_of(self.host_user)

		self.assertIn(event, self.names_in(events["upcoming"]))
		self.assertNotIn(event, self.names_in(events["past"]))

	def test_moves_a_finished_event_to_past(self):
		event = create_event(
			"Wrapped Up",
			self.host_team,
			start_date=add_days(today(), -3),
			end_date=add_days(today(), -1),
		)

		events = self.events_of(self.host_user)

		self.assertIn(event, self.names_in(events["past"]))
		self.assertNotIn(event, self.names_in(events["upcoming"]))

	def test_drops_hosted_events_once_the_membership_is_disabled(self):
		member = create_user("events-lapsed@example.com", "Lapsed")
		membership = add_member(self.host_team, member, "Manager")
		event = create_event("Lapsed Access", self.host_team)
		self.assertIn(event, self.names_in(self.events_of(member)["upcoming"]))

		frappe.set_user("Administrator")
		frappe.db.set_value("Buzz Team Membership", membership, "enabled", 0)

		self.assertNotIn(event, self.names_in(self.events_of(member)["upcoming"]))

	def test_carries_the_organising_team(self):
		frappe.db.set_value("Buzz Team", self.host_team, "logo", "/files/team-logo.png")
		event = create_event("Team Stamped", self.host_team)

		row = next(row for row in self.events_of(self.host_user)["upcoming"] if row["name"] == event)

		self.assertEqual(row["team"], self.host_team)
		self.assertEqual(row["team_name"], "My Events Host Team")
		self.assertEqual(row["team_logo"], "/files/team-logo.png")

	def test_survives_an_event_with_no_team(self):
		event = create_event("Unstamped", self.host_team)
		frappe.db.set_value("Buzz Event", event, "team", None)
		ticket = issue_ticket(event, self.host_user)
		self.assertTrue(ticket)

		row = next(row for row in self.events_of(self.host_user)["upcoming"] if row["name"] == event)

		self.assertIsNone(row["team"])
		self.assertIsNone(row["team_name"])
		self.assertIsNone(row["team_logo"])

	def test_serializes_every_declared_field(self):
		create_event("Payload Shape", self.host_team)

		event = self.events_of(self.host_user)["upcoming"][0]

		self.assertEqual(
			set(event),
			{
				"name",
				"title",
				"route",
				"start_date",
				"end_date",
				"start_time",
				"venue",
				"banner_image",
				"is_host",
				"team",
				"team_name",
				"team_logo",
			},
		)


class TestCreateEvent(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

		if not frappe.db.exists("Event Category", "Meetups"):
			frappe.get_doc({"doctype": "Event Category", "name": "Meetups"}).insert(ignore_permissions=True)

		cls.owner = create_user("create-event-owner@example.com", "Owner")
		cls.viewer = create_user("create-event-viewer@example.com", "Viewer")
		cls.team = create_owned_team("Create Event Team", cls.owner)
		add_member(cls.team, cls.viewer, "Viewer")

	def setUp(self):
		frappe.set_user(self.owner)
		self.addCleanup(frappe.set_user, "Administrator")

	def payload(self, **overrides) -> NewEvent:
		return NewEvent(
			**{
				"team": self.team,
				"title": "Frappeverse Mumbai",
				"start_date": add_days(today(), 30),
				"start_time": "09:00:00",
				"end_time": "17:00:00",
				**overrides,
			}
		)

	def test_creates_an_event_the_team_owns(self):
		created = create_event_endpoint(self.payload())

		event = frappe.get_doc("Buzz Event", created.name)
		self.assertEqual(created.title, "Frappeverse Mumbai")
		self.assertEqual(event.team, self.team)
		self.assertEqual(event.medium, "In Person")
		self.assertEqual(event.category, "Meetups")

	def test_mints_one_host_per_team_and_reuses_it(self):
		first = frappe.get_doc("Buzz Event", create_event_endpoint(self.payload()).name)
		second = frappe.get_doc("Buzz Event", create_event_endpoint(self.payload(title="Second")).name)

		self.assertTrue(first.host)
		self.assertEqual(first.host, second.host)
		self.assertEqual(frappe.db.get_value("Event Host", first.host, "team"), self.team)

	def test_carries_the_optional_fields_through(self):
		created = create_event_endpoint(
			self.payload(
				end_date=add_days(today(), 31),
				about="<p>Come along</p>",
				time_zone="Asia/Kolkata",
			)
		)

		event = frappe.get_doc("Buzz Event", created.name)
		self.assertEqual(event.about, "<p>Come along</p>")
		self.assertEqual(event.time_zone, "Asia/Kolkata")
		# Derived on validate from the zone, so it proves the zone reached the document.
		self.assertEqual(event.time_zone_label, "IST")

	def test_a_viewer_cannot_create_events(self):
		frappe.set_user(self.viewer)

		with self.assertRaises(CannotCreateEvents):
			create_event_endpoint(self.payload())

	def test_a_non_member_cannot_create_events(self):
		stranger = create_user("create-event-stranger@example.com", "Stranger")
		frappe.set_user(stranger)

		with self.assertRaises(CannotCreateEvents):
			create_event_endpoint(self.payload())

	def test_a_venue_from_another_team_is_refused(self):
		"""The reported vector: a manager naming a venue that belongs to someone else.

		Event Venue is autonamed by prompt, so another team's venue name is guessable,
		and the booking confirmation reads the linked venue's address without a
		permission check.
		"""
		stranger = create_user("create-event-venue-stranger@example.com", "Stranger")
		their_team = create_owned_team("Create Event Other Team", stranger)
		theirs = frappe.get_doc(
			{
				"doctype": "Event Venue",
				"__newname": "Create Event Other Team Hall",
				"address": "1 Test Street",
				"team": their_team,
			}
		).insert(ignore_permissions=True)

		with self.assertRaises(frappe.exceptions.ValidationError):
			create_event_endpoint(self.payload(venue=str(theirs.name)))

	def test_zoom_is_refused_when_the_app_is_missing(self):
		if is_app_installed("zoom_integration"):
			self.skipTest("zoom_integration is installed on this site")

		with self.assertRaises(ZoomNotAvailable):
			create_event_endpoint(self.payload(zoom_meeting=True))


class TestGetEvent(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

		cls.owner = create_user("get-event-owner@example.com", "Owner")
		cls.viewer = create_user("get-event-viewer@example.com", "Viewer")
		cls.stranger = create_user("get-event-stranger@example.com", "Stranger")
		cls.team = create_owned_team("Get Event Team", cls.owner)
		add_member(cls.team, cls.viewer, "Viewer")

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")

	def test_returns_the_fields_the_manage_page_edits(self):
		event = create_event(
			"Detailed Event",
			self.team,
			short_description="A short one",
			about="<p>A long one</p>",
			medium="Online",
			meeting_link="https://example.com/join",
		)
		frappe.set_user(self.owner)

		detail = get_event(event).__json__()

		self.assertEqual(detail["name"], event)
		self.assertEqual(detail["short_description"], "A short one")
		self.assertEqual(detail["about"], "<p>A long one</p>")
		self.assertEqual(detail["medium"], "Online")
		self.assertEqual(detail["meeting_link"], "https://example.com/join")
		self.assertIsNone(detail["venue"])

	def test_resolves_the_venue_with_its_address(self):
		venue = frappe.get_doc(
			{
				"doctype": "Event Venue",
				"name": "Get Event Venue",
				"address": "12 Example Street",
				"team": self.team,
			}
		).insert(ignore_permissions=True)
		event = create_event("Venued Event", self.team, venue=venue.name)
		frappe.set_user(self.owner)

		detail = get_event(event).__json__()

		self.assertEqual(detail["venue"]["name"], venue.name)
		self.assertEqual(detail["venue"]["address"], "12 Example Street")

	def test_a_viewer_cannot_open_the_manage_payload(self):
		event = create_event("Viewer Event", self.team)
		frappe.set_user(self.viewer)

		with self.assertRaises(CannotManageEvent):
			get_event(event)

	def test_a_non_member_cannot_open_the_manage_payload(self):
		event = create_event("Stranger Event", self.team)
		frappe.set_user(self.stranger)

		with self.assertRaises(CannotManageEvent):
			get_event(event)

	def test_an_unknown_event_is_not_found(self):
		frappe.set_user(self.owner)

		with self.assertRaises(EventNotFound):
			get_event("999999999")


class TestCheckEventRoute(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

		cls.owner = create_user("check-route-owner@example.com", "Owner")
		cls.team = create_owned_team("Check Route Team", cls.owner)

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")

	def test_an_unused_route_is_available(self):
		frappe.set_user(self.owner)

		self.assertTrue(check_event_route("a-route-nobody-has").available)

	def test_a_route_another_event_holds_is_taken(self):
		create_event("Route Holder", self.team, route="taken-route")
		frappe.set_user(self.owner)

		self.assertFalse(check_event_route("taken-route").available)

	def test_an_unpublished_event_still_holds_its_route(self):
		create_event("Draft Route Holder", self.team, route="draft-route", is_published=0)
		frappe.set_user(self.owner)

		self.assertFalse(check_event_route("draft-route").available)

	def test_an_event_does_not_block_its_own_route(self):
		event = create_event("Self Route", self.team, route="own-route")
		frappe.set_user(self.owner)

		self.assertTrue(check_event_route("own-route", event=event).available)

	def test_a_reserved_route_is_refused(self):
		frappe.set_user(self.owner)

		self.assertFalse(check_event_route("account").available)

	def test_a_blank_route_is_not_available(self):
		frappe.set_user(self.owner)

		self.assertFalse(check_event_route("   ").available)


class TestGetEventGuests(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

		cls.owner = create_user("guests-owner@example.com", "Owner")
		cls.stranger = create_user("guests-stranger@example.com", "Stranger")
		cls.team = create_owned_team("Guests Team", cls.owner)

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")

	def test_counts_and_lists_the_submitted_tickets(self):
		event = create_event("Guested Event", self.team)
		issue_ticket(event, "guest-one@example.com")
		issue_ticket(event, "guest-two@example.com")
		frappe.set_user(self.owner)

		guests = get_event_guests(event).__json__()

		self.assertEqual(guests["total"], 2)
		self.assertEqual(len(guests["guests"]), 2)
		emails = {guest["attendee_email"] for guest in guests["guests"]}
		self.assertEqual(emails, {"guest-one@example.com", "guest-two@example.com"})

	def test_leaves_out_a_ticket_that_was_never_submitted(self):
		event = create_event("Draft Ticket Event", self.team)
		create_ticket(event, "draft-guest@example.com")
		frappe.set_user(self.owner)

		self.assertEqual(get_event_guests(event).total, 0)

	def test_carries_the_add_ons_a_ticket_holds(self):
		event = create_event("Add-on Event", self.team)
		ticket = issue_ticket(event, "addon-guest@example.com")
		add_on = frappe.get_doc(
			{"doctype": "Ticket Add-on", "event": event, "title": "T-Shirt", "price": 0}
		).insert(ignore_permissions=True)
		# Submitted, so the row goes on through db_insert rather than a save.
		frappe.get_doc(
			{
				"doctype": "Ticket Add-on Value",
				"parenttype": "Event Ticket",
				"parentfield": "add_ons",
				"parent": ticket,
				"add_on": add_on.name,
				"value": "Large",
			}
		).db_insert()
		frappe.set_user(self.owner)

		guest = get_event_guests(event).guests[0]

		self.assertEqual(len(guest.add_ons), 1)
		self.assertEqual(guest.add_ons[0].title, "T-Shirt")
		self.assertEqual(guest.add_ons[0].value, "Large")

	def test_names_the_ticket_type_rather_than_its_docname(self):
		event = create_event("Typed Ticket Event", self.team)
		ticket = issue_ticket(event, "typed-guest@example.com")
		ticket_type = frappe.db.get_value("Event Ticket", ticket, "ticket_type")
		title = frappe.db.get_value("Event Ticket Type", ticket_type, "title")
		frappe.set_user(self.owner)

		guest = get_event_guests(event).guests[0]

		self.assertEqual(guest.ticket_type, title)
		self.assertNotEqual(guest.ticket_type, ticket_type)

	def test_an_event_with_no_guests_is_empty_rather_than_an_error(self):
		event = create_event("Quiet Event", self.team)
		frappe.set_user(self.owner)

		guests = get_event_guests(event)

		self.assertEqual(guests.total, 0)
		self.assertEqual(guests.guests, [])

	def test_a_non_member_cannot_read_the_guest_list(self):
		event = create_event("Private Guests", self.team)
		issue_ticket(event, "private-guest@example.com")
		frappe.set_user(self.stranger)

		with self.assertRaises(CannotManageEvent):
			get_event_guests(event)

	def test_an_unknown_event_is_not_found(self):
		frappe.set_user(self.owner)

		with self.assertRaises(EventNotFound):
			get_event_guests("999999999")
