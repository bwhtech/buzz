import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, today
from pydantic import ValidationError

from buzz.api.events import (
	check_event_route,
	get_event,
	get_event_guests,
	get_event_registration_trend,
	get_my_events,
	set_registration_state,
)
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

	def events_of(self, user: str, **filters) -> dict[str, list[dict]]:
		frappe.set_user(user)
		return get_my_events(filters or None).__json__()

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

	def test_a_role_filter_keeps_only_hosted_events(self):
		hosted = create_event("Role Filter Hosted", self.host_team)
		ticketed = create_event("Role Filter Ticketed", self.other_team)
		issue_ticket(ticketed, self.host_user)

		names = self.names_in(self.events_of(self.host_user, role="hosting")["upcoming"])

		self.assertIn(hosted, names)
		self.assertNotIn(ticketed, names)

	def test_a_role_filter_keeps_only_ticketed_events(self):
		hosted = create_event("Role Filter Own", self.host_team)
		ticketed = create_event("Role Filter Guest", self.other_team)
		issue_ticket(ticketed, self.host_user)

		names = self.names_in(self.events_of(self.host_user, role="attending")["upcoming"])

		self.assertIn(ticketed, names)
		self.assertNotIn(hosted, names)

	def test_a_team_filter_keeps_only_that_teams_events(self):
		mine = create_event("Team Filter Mine", self.host_team)
		theirs = create_event("Team Filter Theirs", self.other_team)
		issue_ticket(theirs, self.host_user)

		names = self.names_in(self.events_of(self.host_user, team=self.host_team)["upcoming"])

		self.assertIn(mine, names)
		self.assertNotIn(theirs, names)

	def test_a_medium_filter_keeps_only_that_medium(self):
		online = create_event("Medium Online", self.host_team, medium="Online")
		in_person = create_event("Medium In Person", self.host_team, medium="In Person")

		names = self.names_in(self.events_of(self.host_user, medium="Online")["upcoming"])

		self.assertIn(online, names)
		self.assertNotIn(in_person, names)

	def test_an_unknown_filter_value_is_refused(self):
		with self.assertRaises(ValidationError):
			self.events_of(self.host_user, role="lurking")

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
				"end_time",
				"venue",
				"medium",
				"banner_image",
				"is_host",
				"is_attendee",
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
		self.assertTrue(detail["modified"])

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

	def test_reports_registrations_closed_once_the_cutoff_has_passed(self):
		event = create_event("Closed Event", self.team, registrations_close_at="2020-01-01 00:00:00")
		frappe.set_user(self.owner)

		self.assertTrue(get_event_guests(event).registrations_closed)

	def test_reports_registrations_open_before_the_event_ends(self):
		event = create_event("Open Event", self.team)
		frappe.set_user(self.owner)

		self.assertFalse(get_event_guests(event).registrations_closed)

	def test_names_the_event_for_a_member_who_cannot_edit_it(self):
		"""The header labels the page off this payload, so read access has to be enough."""
		event = create_event("Named Event", self.team)
		viewer = create_user("guests-viewer@example.com", "Viewer")
		add_member(self.team, viewer, "Viewer")
		frappe.set_user(viewer)

		self.assertEqual(get_event_guests(event).title, "Event Named Event")
		with self.assertRaises(CannotManageEvent):
			get_event(event)

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


class TestGetEventGuestsPaging(IntegrationTestCase):
	"""Search, order and paging — the arguments the guest list walks the roll with."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

		cls.owner = create_user("paging-owner@example.com", "Owner")
		cls.team = create_owned_team("Paging Team", cls.owner)

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")

	def registered(self, event: str, email: str, name: str, at: str) -> str:
		"""A ticket with a name on it and a registration time of its own.

		Tickets a test writes land in the same second, so `creation` is set explicitly —
		otherwise the order under test is decided by the name hash.
		"""
		ticket = issue_ticket(event, email)
		frappe.db.set_value(
			"Event Ticket",
			ticket,
			{"first_name": name, "attendee_name": name, "creation": at},
			update_modified=False,
		)
		return ticket

	def roll_call(self, event: str) -> None:
		self.registered(event, "ana@example.com", "Ana Diaz", "2026-01-01 09:00:00")
		self.registered(event, "bo@example.com", "Bo Chen", "2026-01-02 09:00:00")
		self.registered(event, "cy@example.com", "Cy Ferreira", "2026-01-03 09:00:00")

	def test_carries_the_time_the_ticket_was_raised(self):
		event = create_event("Registered At Event", self.team)
		self.registered(event, "ana@example.com", "Ana Diaz", "2026-01-01 09:00:00")
		frappe.set_user(self.owner)

		guest = get_event_guests(event).guests[0]

		self.assertEqual(str(guest.registered_at), "2026-01-01 09:00:00")

	def test_newest_registration_comes_first_by_default(self):
		event = create_event("Ordered Event", self.team)
		self.roll_call(event)
		frappe.set_user(self.owner)

		names = [guest.attendee_name for guest in get_event_guests(event).guests]

		self.assertEqual(names, ["Cy Ferreira", "Bo Chen", "Ana Diaz"])

	def test_asc_walks_from_the_oldest_registration(self):
		event = create_event("Ascending Event", self.team)
		self.roll_call(event)
		frappe.set_user(self.owner)

		names = [guest.attendee_name for guest in get_event_guests(event, order="asc").guests]

		self.assertEqual(names, ["Ana Diaz", "Bo Chen", "Cy Ferreira"])

	def test_an_unknown_order_falls_back_to_newest_first(self):
		event = create_event("Odd Order Event", self.team)
		self.roll_call(event)
		frappe.set_user(self.owner)

		guests = get_event_guests(event, order="name desc; drop table")

		self.assertEqual(guests.guests[0].attendee_name, "Cy Ferreira")

	def test_a_page_carries_only_its_own_slice(self):
		event = create_event("Paged Event", self.team)
		self.roll_call(event)
		frappe.set_user(self.owner)

		first = get_event_guests(event, limit=2)

		self.assertEqual([guest.attendee_name for guest in first.guests], ["Cy Ferreira", "Bo Chen"])
		self.assertTrue(first.has_next_page)

	def test_the_last_page_says_there_is_nothing_after_it(self):
		event = create_event("Last Page Event", self.team)
		self.roll_call(event)
		frappe.set_user(self.owner)

		last = get_event_guests(event, start=2, limit=2)

		self.assertEqual([guest.attendee_name for guest in last.guests], ["Ana Diaz"])
		self.assertFalse(last.has_next_page)

	def test_a_full_final_page_is_still_the_end(self):
		"""Three guests read two at a time: the second page fills, and nothing follows."""
		event = create_event("Even Page Event", self.team)
		self.roll_call(event)
		self.registered(event, "di@example.com", "Di Okafor", "2026-01-04 09:00:00")
		frappe.set_user(self.owner)

		self.assertFalse(get_event_guests(event, start=2, limit=2).has_next_page)

	def test_search_matches_a_name(self):
		event = create_event("Name Search Event", self.team)
		self.roll_call(event)
		frappe.set_user(self.owner)

		guests = get_event_guests(event, search="chen")

		self.assertEqual([guest.attendee_name for guest in guests.guests], ["Bo Chen"])

	def test_search_matches_an_email(self):
		event = create_event("Email Search Event", self.team)
		self.roll_call(event)
		frappe.set_user(self.owner)

		guests = get_event_guests(event, search="cy@")

		self.assertEqual([guest.attendee_email for guest in guests.guests], ["cy@example.com"])

	def test_search_reports_the_match_count_beside_the_registered_count(self):
		event = create_event("Counted Search Event", self.team)
		self.roll_call(event)
		frappe.set_user(self.owner)

		guests = get_event_guests(event, search="chen")

		self.assertEqual(guests.total, 3)
		self.assertEqual(guests.matched, 1)

	def test_without_a_search_every_guest_is_a_match(self):
		event = create_event("Unsearched Event", self.team)
		self.roll_call(event)
		frappe.set_user(self.owner)

		guests = get_event_guests(event)

		self.assertEqual(guests.matched, guests.total)

	def test_a_search_that_matches_nobody_is_empty_rather_than_an_error(self):
		event = create_event("Empty Search Event", self.team)
		self.roll_call(event)
		frappe.set_user(self.owner)

		guests = get_event_guests(event, search="nobody-here")

		self.assertEqual(guests.guests, [])
		self.assertEqual(guests.matched, 0)
		self.assertEqual(guests.total, 3)
		self.assertFalse(guests.has_next_page)

	def test_blank_search_is_not_a_filter(self):
		event = create_event("Blank Search Event", self.team)
		self.roll_call(event)
		frappe.set_user(self.owner)

		self.assertEqual(len(get_event_guests(event, search="   ").guests), 3)


class TestGetEventGuestsTicketTypeFilter(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

		cls.owner = create_user("types-owner@example.com", "Owner")
		cls.team = create_owned_team("Ticket Types Team", cls.owner)

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")

	def two_types(self, event: str) -> tuple[str, str]:
		"""One ticket on each of two types, returning the types in that order."""
		first = frappe.db.get_value("Event Ticket", issue_ticket(event, "early@example.com"), "ticket_type")
		second = frappe.db.get_value("Event Ticket", issue_ticket(event, "late@example.com"), "ticket_type")
		return str(first), str(second)

	def test_lists_the_types_the_event_sells(self):
		"""Every type, not only the ones someone has bought — an empty tier is still a filter."""
		event = create_event("Typed Filter Event", self.team)
		first, second = self.two_types(event)
		frappe.set_user(self.owner)

		names = {ticket_type.name for ticket_type in get_event_guests(event).ticket_types}

		self.assertLessEqual({first, second}, names)

	def test_narrows_the_list_to_the_chosen_type(self):
		event = create_event("Narrowed Event", self.team)
		first, _ = self.two_types(event)
		frappe.set_user(self.owner)

		guests = get_event_guests(event, ticket_types=first)

		self.assertEqual([guest.attendee_email for guest in guests.guests], ["early@example.com"])
		self.assertEqual(guests.matched, 1)
		self.assertEqual(guests.total, 2)

	def test_several_types_are_read_as_any_of_them(self):
		event = create_event("Any Type Event", self.team)
		first, second = self.two_types(event)
		frappe.set_user(self.owner)

		guests = get_event_guests(event, ticket_types=f"{first},{second}")

		self.assertEqual(guests.matched, 2)

	def test_no_chosen_type_is_not_a_filter(self):
		event = create_event("Untyped Filter Event", self.team)
		self.two_types(event)
		frappe.set_user(self.owner)

		self.assertEqual(len(get_event_guests(event, ticket_types="  ").guests), 2)

	def test_search_and_type_narrow_together(self):
		event = create_event("Combined Filter Event", self.team)
		first, _ = self.two_types(event)
		frappe.set_user(self.owner)

		self.assertEqual(get_event_guests(event, search="late@", ticket_types=first).matched, 0)
		self.assertEqual(get_event_guests(event, search="early@", ticket_types=first).matched, 1)


class TestGetEventRegistrationTrend(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

		cls.owner = create_user("trend-owner@example.com", "Owner")
		cls.stranger = create_user("trend-stranger@example.com", "Stranger")
		cls.team = create_owned_team("Trend Team", cls.owner)

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")

	def registered_on(self, event: str, email: str, day: str) -> str:
		ticket = issue_ticket(event, email)
		frappe.db.set_value("Event Ticket", ticket, "creation", f"{day} 10:00:00", update_modified=False)
		return frappe.db.get_value("Event Ticket", ticket, "ticket_type")

	def totals_by_day(self, trend) -> dict:
		"""The stack's own height: every type of a day summed back together."""
		totals: dict = {}
		for row in trend.per_day:
			totals[row.date] = totals.get(row.date, 0) + row.count
		return totals

	def test_counts_the_tickets_raised_on_each_day(self):
		event = create_event("Trended Event", self.team)
		self.registered_on(event, "today-one@example.com", today())
		self.registered_on(event, "today-two@example.com", today())
		self.registered_on(event, "yesterday@example.com", add_days(today(), -1))
		frappe.set_user(self.owner)

		trend = get_event_registration_trend(event, days=3)

		totals = self.totals_by_day(trend)
		self.assertEqual(totals[getdate(today())], 2)
		self.assertEqual(totals[getdate(add_days(today(), -1))], 1)
		self.assertEqual(trend.total, 3)

	def test_splits_a_day_by_ticket_type(self):
		event = create_event("Split Event", self.team)
		# create_ticket raises a type of its own per ticket, so these are two tiers.
		first = self.registered_on(event, "tier-one@example.com", today())
		second = self.registered_on(event, "tier-two@example.com", today())
		titles = {
			str(first): frappe.db.get_value("Event Ticket Type", first, "title"),
			str(second): frappe.db.get_value("Event Ticket Type", second, "title"),
		}
		frappe.set_user(self.owner)

		trend = get_event_registration_trend(event, days=2)

		today_rows = {row.ticket_type: row.count for row in trend.per_day if row.date == getdate(today())}
		for title in titles.values():
			self.assertEqual(today_rows[title], 1)

	def test_a_quiet_day_is_a_zero_rather_than_a_gap(self):
		event = create_event("Quiet Day Event", self.team)
		self.registered_on(event, "quiet@example.com", today())
		frappe.set_user(self.owner)

		trend = get_event_registration_trend(event, days=7)

		totals = self.totals_by_day(trend)
		self.assertEqual(len(totals), 7)
		self.assertEqual(sorted(totals.values()), [0] * 6 + [1])

	def test_every_type_is_drawn_on_every_day(self):
		"""A band that vanishes mid-stack reads as a break in the chart, not as nobody buying."""
		event = create_event("Gridded Event", self.team)
		self.registered_on(event, "gridded@example.com", today())
		frappe.set_user(self.owner)

		trend = get_event_registration_trend(event, days=4)

		types = {row.ticket_type for row in trend.per_day}
		self.assertEqual(len(trend.per_day), 4 * len(types))

	def test_the_window_ends_on_today(self):
		event = create_event("Windowed Event", self.team)
		self.registered_on(event, "windowed@example.com", today())
		frappe.set_user(self.owner)

		trend = get_event_registration_trend(event, days=5)

		self.assertEqual(trend.per_day[-1].date, getdate(today()))
		self.assertEqual(trend.per_day[0].date, getdate(add_days(today(), -4)))

	def test_names_the_ticket_type_rather_than_its_docname(self):
		event = create_event("Named Type Trend", self.team)
		ticket_type = self.registered_on(event, "named-type@example.com", today())
		title = frappe.db.get_value("Event Ticket Type", ticket_type, "title")
		frappe.set_user(self.owner)

		trend = get_event_registration_trend(event, days=2)

		self.assertIn(title, {row.ticket_type for row in trend.per_day})
		self.assertNotIn(str(ticket_type), {row.ticket_type for row in trend.per_day})

	def test_leaves_out_a_ticket_that_was_never_submitted(self):
		event = create_event("Draft Trend Event", self.team)
		create_ticket(event, "draft-trend@example.com")
		frappe.set_user(self.owner)

		trend = get_event_registration_trend(event)

		self.assertEqual(trend.total, 0)
		self.assertEqual({row.count for row in trend.per_day}, {0})

	def test_the_type_breakdown_counts_registrations_older_than_the_window(self):
		"""It sits beside the all-time total, so a fortnight's slice would not add up to it."""
		event = create_event("Long Running Event", self.team)
		self.registered_on(event, "ancient@example.com", add_days(today(), -60))
		frappe.set_user(self.owner)

		trend = get_event_registration_trend(event, days=7)

		self.assertEqual(sum(row.count for row in trend.by_ticket_type), trend.total)
		self.assertEqual({row.count for row in trend.per_day}, {0})

	def test_the_type_breakdown_names_the_type_rather_than_its_docname(self):
		event = create_event("Named Breakdown", self.team)
		ticket_type = self.registered_on(event, "named-breakdown@example.com", today())
		title = frappe.db.get_value("Event Ticket Type", ticket_type, "title")
		frappe.set_user(self.owner)

		trend = get_event_registration_trend(event)

		self.assertIn(title, {row.ticket_type for row in trend.by_ticket_type})

	def test_a_non_member_cannot_read_the_trend(self):
		event = create_event("Private Trend", self.team)
		frappe.set_user(self.stranger)

		with self.assertRaises(CannotManageEvent):
			get_event_registration_trend(event)

	def test_an_unknown_event_is_not_found(self):
		frappe.set_user(self.owner)

		with self.assertRaises(EventNotFound):
			get_event_registration_trend("999999999")


class TestSetRegistrationState(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

		cls.owner = create_user("registration-owner@example.com", "Owner")
		cls.viewer = create_user("registration-viewer@example.com", "Viewer")
		cls.team = create_owned_team("Registration Team", cls.owner)
		add_member(cls.team, cls.viewer, "Viewer")

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")

	def test_closing_stops_registrations_now_in_the_events_own_timezone(self):
		"""A UTC wall clock would sit hours ahead of an event west of UTC, leaving it open."""
		event = create_event("Pacific Event", self.team, time_zone="US/Pacific")
		frappe.set_user(self.owner)

		self.assertTrue(set_registration_state(event, closed=True).registrations_closed)
		self.assertTrue(get_event_guests(event).registrations_closed)

	def test_opening_clears_the_cutoff(self):
		event = create_event("Reopened Event", self.team, registrations_close_at="2020-01-01 00:00:00")
		frappe.set_user(self.owner)

		self.assertFalse(set_registration_state(event, closed=False).registrations_closed)
		self.assertIsNone(frappe.db.get_value("Buzz Event", event, "registrations_close_at"))

	def test_an_ended_event_stays_closed_when_it_is_opened(self):
		"""Clearing the cutoff cannot reopen it, so the answer says closed rather than done."""
		event = create_event(
			"Finished Event",
			self.team,
			start_date=add_days(today(), -10),
			end_date=add_days(today(), -9),
		)
		frappe.set_user(self.owner)

		self.assertTrue(set_registration_state(event, closed=False).registrations_closed)

	def test_a_reader_cannot_change_the_registration_state(self):
		event = create_event("Guarded Event", self.team)
		frappe.set_user(self.viewer)

		with self.assertRaises(CannotManageEvent):
			set_registration_state(event, closed=True)

	def test_the_guest_response_tells_a_reader_they_cannot_write(self):
		event = create_event("Read Only Event", self.team)

		frappe.set_user(self.viewer)
		self.assertFalse(get_event_guests(event).can_write)

		frappe.set_user(self.owner)
		self.assertTrue(get_event_guests(event).can_write)

	def test_an_external_registration_page_is_linked_instead_of_the_buzz_one(self):
		event = create_event(
			"External Event",
			self.team,
			external_registration_page=1,
			registration_url="https://tickets.example.com/buzz",
		)
		frappe.set_user(self.owner)

		self.assertEqual(get_event_guests(event).registration_link, "https://tickets.example.com/buzz")

	def test_an_ordinary_event_is_linked_to_its_own_registration_page(self):
		event = create_event("Hosted Event", self.team, route="hosted-event")
		frappe.set_user(self.owner)

		self.assertEqual(get_event_guests(event).registration_link, "/b/register/hosted-event")
