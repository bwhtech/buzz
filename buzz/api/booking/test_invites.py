import frappe
from frappe.utils import add_days, today

from buzz.api.booking.exceptions import (
	InviteExpired,
	InviteNotFound,
	InviteNotOpen,
	RequestNotOpen,
	TooManyInvites,
)
from buzz.api.booking.invites import (
	accept_invite,
	add_guests,
	decline_invite,
	get_invite,
	read_invite_sheet,
	send_invites,
)
from buzz.api.booking.requests import reopen_request
from buzz.api.booking.services import get_booking_access_token
from buzz.api.events.exceptions import CannotManageEvent
from buzz.tests.base_test_cases import BookingTestCase
from buzz.tests.factories import (
	BuzzEventFactory,
	EventBookingFactory,
	EventTicketFactory,
	EventTicketTypeFactory,
)
from buzz.tests.utils import html_part, mute_outgoing_email


class InviteTestCase(BookingTestCase):
	"""A fresh event per test, so invites never pile up on a shared one."""

	def setUp(self):
		self.event = BuzzEventFactory.create()
		self.event.reload()
		super().setUp()
		mute_outgoing_email(self)
		self.paid_ticket_type = EventTicketTypeFactory.create("paid", event=self.event.name)

	def invite(self, email: str, ticket_type=None, **values) -> str:
		ticket_type = str(ticket_type or self.paid_ticket_type.name)
		outcomes = send_invites(
			str(self.event.name), [{"email": email, "ticket_type": ticket_type, **values}]
		)
		return outcomes[0].booking

	def booking(self, name: str):
		return frappe.get_doc("Event Booking", name)

	def emails_of(self, name: str) -> list[str]:
		rows = frappe.get_all(
			"Email Queue",
			filters={"reference_doctype": "Event Booking", "reference_name": name},
			pluck="message",
			order_by="creation asc",
		)
		return [html_part(message) for message in rows]


class TestInviteAccepted(InviteTestCase):
	def test_invite_is_a_free_draft_emailed_with_its_link(self):
		name = self.invite("invitee-one@example.com")

		booking = self.booking(name)
		self.assertEqual((booking.status, booking.docstatus, booking.request_type), ("Invited", 0, "Invite"))
		self.assertEqual(booking.total_amount, 0)
		self.assertEqual(booking.user, "invitee-one@example.com")
		self.assertEqual(frappe.db.count("Event Ticket", {"booking": name}), 0)
		self.assertIn(f"/b/invite/{name}?token={get_booking_access_token(name)}", self.emails_of(name)[0])

	def test_guest_reads_the_invite_with_its_token(self):
		name = self.invite("invitee-two@example.com")

		with self.set_user("Guest"):
			invite = get_invite(name, get_booking_access_token(name))

		self.assertEqual(invite.event_title, self.event.title)
		self.assertEqual(invite.ticket_type, self.paid_ticket_type.title)
		self.assertEqual(invite.status, "Invited")
		# The email prefix stands in for a name nobody gave, so the guest types their own.
		self.assertIsNone(invite.first_name)

	def test_accepting_issues_the_ticket_without_payment(self):
		name = self.invite("invitee-three@example.com")

		with self.set_user("Guest"):
			accept_invite(name, get_booking_access_token(name), "Meera", "Nair")

		booking = self.booking(name)
		self.assertEqual(
			(booking.status, booking.docstatus, booking.payment_status), ("Confirmed", 1, "Paid")
		)
		self.assertEqual(booking.total_amount, 0)
		ticket = frappe.get_doc("Event Ticket", {"booking": name})
		self.assertEqual((ticket.first_name, ticket.last_name), ("Meera", "Nair"))
		self.assertEqual(ticket.attendee_email, "invitee-three@example.com")

	def test_hidden_and_sold_out_tiers_can_be_invited(self):
		hidden = EventTicketTypeFactory.create("is_hidden", event=self.event.name, max_tickets_available=1)
		EventTicketFactory.create("submitted", event=self.event.name, ticket_type=hidden.name)
		name = self.invite("hidden-tier@example.com", hidden.name)

		with self.set_user("Guest"):
			accept_invite(name, get_booking_access_token(name), "Isha")

		self.assertEqual(self.booking(name).docstatus, 1)


class TestInviteAnswered(InviteTestCase):
	def test_declining_keeps_the_invite_as_rejected(self):
		name = self.invite("decliner@example.com")

		with self.set_user("Guest"):
			decline_invite(name, get_booking_access_token(name))

		booking = self.booking(name)
		self.assertEqual((booking.status, booking.docstatus), ("Rejected", 0))
		with self.set_user("Guest"), self.assertRaises(InviteNotOpen):
			accept_invite(name, get_booking_access_token(name), "Dev")

	def test_an_invite_is_accepted_once(self):
		name = self.invite("twice@example.com")
		token = get_booking_access_token(name)

		with self.set_user("Guest"):
			accept_invite(name, token, "Dev")
			with self.assertRaises(InviteNotOpen):
				accept_invite(name, token, "Dev")

	def test_registering_meanwhile_closes_the_invite(self):
		name = self.invite("registered-meanwhile@example.com")
		EventTicketFactory.create(
			"submitted",
			event=self.event.name,
			ticket_type=self.paid_ticket_type.name,
			attendee_email="registered-meanwhile@example.com",
		)

		with self.set_user("Guest"), self.assertRaises(InviteNotOpen):
			accept_invite(name, get_booking_access_token(name), "Rohan")

	def test_a_declined_invite_is_not_a_request_to_reopen(self):
		name = self.invite("not-reopened@example.com")
		with self.set_user("Guest"):
			decline_invite(name, get_booking_access_token(name))

		with self.assertRaises(RequestNotOpen):
			reopen_request(name)

	def test_a_booking_cannot_make_itself_an_invite(self):
		booking = EventBookingFactory.create(event=self.event.name)
		booking.request_type = "Invite"

		with self.assertRaises(frappe.PermissionError):
			booking.save()

	def test_a_wrong_token_finds_nothing(self):
		name = self.invite("wrong-token@example.com")

		with self.set_user("Guest"), self.assertRaises(InviteNotFound):
			get_invite(name, "not-the-token")

	def test_a_regular_booking_is_not_an_invite(self):
		booking = EventBookingFactory.create(event=self.event.name).name

		with self.set_user("Guest"), self.assertRaises(InviteNotFound):
			get_invite(booking, get_booking_access_token(booking))

	def test_an_ended_event_closes_its_invites(self):
		name = self.invite("too-late@example.com")
		self.set_event({"start_date": add_days(today(), -3), "end_date": add_days(today(), -1)})

		with self.set_user("Guest"), self.assertRaises(InviteExpired):
			accept_invite(name, get_booking_access_token(name), "Tara")


class TestInviteBatch(InviteTestCase):
	def test_existing_guests_and_repeats_are_skipped(self):
		EventTicketFactory.create(
			"submitted",
			event=self.event.name,
			ticket_type=self.paid_ticket_type.name,
			attendee_email="holder@example.com",
		)
		self.invite("pending@example.com")
		ticket_type = str(self.paid_ticket_type.name)
		rows = [
			{"email": email, "ticket_type": ticket_type}
			for email in (
				"holder@example.com",
				"Pending@example.com",
				"fresh@example.com",
				"fresh@example.com",
			)
		]

		outcomes = send_invites(str(self.event.name), rows)

		self.assertEqual(
			[(row.email, row.status) for row in outcomes],
			[
				("holder@example.com", "registered"),
				("pending@example.com", "already invited"),
				("fresh@example.com", "invited"),
			],
		)

	def test_the_message_is_capped(self):
		rows = [{"email": "long-note@example.com", "ticket_type": str(self.paid_ticket_type.name)}]

		with self.assertRaises(frappe.ValidationError):
			send_invites(str(self.event.name), rows, "x" * 301)

	def test_the_message_is_escaped_in_the_email(self):
		ticket_type = str(self.paid_ticket_type.name)
		rows = [{"email": "escaped@example.com", "ticket_type": ticket_type}]

		name = send_invites(str(self.event.name), rows, "<a href='x'>click</a>")[0].booking

		self.assertIn("&lt;a href=", self.emails_of(name)[0])

	def test_a_batch_is_capped(self):
		rows = [{"email": f"guest{index}@example.com", "ticket_type": "1"} for index in range(51)]

		with self.assertRaises(TooManyInvites):
			send_invites(str(self.event.name), rows)

	def test_only_the_guest_list_editors_invite(self):
		with self.set_user(self.outsider), self.assertRaises(CannotManageEvent):
			self.invite("nobody@example.com")


class TestAddDirectly(InviteTestCase):
	def test_adding_directly_books_a_free_ticket_at_once(self):
		rows = [
			{
				"email": "direct@example.com",
				"first_name": "Ananya",
				"last_name": "Das",
				"ticket_type": str(self.paid_ticket_type.name),
			}
		]

		outcome = add_guests(str(self.event.name), rows)[0]

		booking = self.booking(outcome.booking)
		self.assertEqual(outcome.status, "added")
		self.assertEqual((booking.status, booking.docstatus, booking.total_amount), ("Confirmed", 1, 0))
		ticket = frappe.get_doc("Event Ticket", {"booking": outcome.booking})
		self.assertEqual((ticket.first_name, ticket.last_name), ("Ananya", "Das"))

	def test_adding_directly_needs_a_name(self):
		rows = [{"email": "nameless@example.com", "ticket_type": str(self.paid_ticket_type.name)}]

		with self.assertRaises(frappe.ValidationError):
			add_guests(str(self.event.name), rows)


class TestInviteSheet(InviteTestCase):
	def test_a_sheet_reads_into_invite_rows(self):
		text = "First Name,Last name,E-mail,Tier\nPriya,Raman,priya@example.com,VIP\n,,sana@example.com,\n"

		rows = read_invite_sheet(str(self.event.name), text=text)

		self.assertEqual(
			[row.model_dump() for row in rows],
			[
				{"first_name": "Priya", "last_name": "Raman", "email": "priya@example.com", "tier": "VIP"},
				{"first_name": "", "last_name": "", "email": "sana@example.com", "tier": ""},
			],
		)

	def test_a_sheet_past_the_batch_limit_is_refused(self):
		text = "Email\n" + "\n".join(f"guest{index}@example.com" for index in range(51))

		with self.assertRaises(TooManyInvites):
			read_invite_sheet(str(self.event.name), text=text)
