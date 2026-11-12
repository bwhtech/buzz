import json

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.events.collaborators import get_event_access
from buzz.api.events.exceptions import CannotManageEvent
from buzz.api.filters.exceptions import InvalidFilter
from buzz.api.transactions import get_event_transactions, get_transaction, get_transaction_summary
from buzz.api.transactions.exceptions import TransactionNotFound
from buzz.tests.base_test_cases import make_payment_gateway
from buzz.tests.factories import (
	BuzzEventCollaboratorFactory,
	BuzzEventFactory,
	BuzzTeamFactory,
	BuzzTeamMembershipFactory,
	EventBookingFactory,
	EventPaymentFactory,
	EventTicketTypeFactory,
	UserFactory,
)

TICKET_PRICE = 1000


def member(team: str, email: str, team_role: str) -> str:
	user = UserFactory.create_once(email).name
	BuzzTeamMembershipFactory.create(team=team, user=user, team_role=team_role)
	return user


def collaborator(event: str, email: str, **sections) -> str:
	BuzzEventCollaboratorFactory.create("accepted", event=event, email=email, **sections)
	return email


class TransactionsTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once("transactions-owner@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.owner).name
		cls.admin = member(cls.team, "transactions-admin@example.com", "Admin")
		cls.manager = member(cls.team, "transactions-manager@example.com", "Manager")
		cls.viewer = member(cls.team, "transactions-viewer@example.com", "Viewer")
		cls.frontdesk = member(cls.team, "transactions-frontdesk@example.com", "Frontdesk")
		other_team = BuzzTeamFactory.create_owned_by(cls.owner).name
		cls.other_manager = member(other_team, "transactions-other-manager@example.com", "Manager")
		cls.attendee = UserFactory.create_once("transactions-attendee@example.com").name
		cls.gateway = make_payment_gateway()

		cls.event = str(BuzzEventFactory.create(team=cls.team, title="Money Event").name)
		cls.other_event = str(BuzzEventFactory.create(team=cls.team).name)
		cls.ticket_type = EventTicketTypeFactory.create(
			event=cls.event, title="General", prices=[{"currency": "INR", "price": TICKET_PRICE}]
		).name
		cls.ticketing_viewer = collaborator(
			cls.event, "transactions-ticketing@example.com", ticketing_access="View"
		)
		cls.ticketing_editor = collaborator(
			cls.event, "transactions-ticketing-edit@example.com", ticketing_access="Edit"
		)
		cls.guests_viewer = collaborator(cls.event, "transactions-guests@example.com", guests_access="View")
		cls.guests_editor = collaborator(
			cls.event, "transactions-guests-edit@example.com", guests_access="Edit"
		)

		cls.paid = cls.create_booking(cls.event, attendees=2, user=cls.attendee)
		cls.payment = EventPaymentFactory.create(
			"received",
			reference_doctype="Event Booking",
			reference_docname=cls.paid.name,
			payment_gateway=cls.gateway,
			amount=cls.paid.total_amount,
		)
		cls.pending = cls.create_booking(
			cls.event,
			submit=False,
			payment_status="Verification Pending",
			payment_method="Offline",
			offline_payment_method="Bank Transfer",
		)
		cls.unpaid_draft = cls.create_booking(cls.event, submit=False, payment_status="Unpaid")
		free_type = EventTicketTypeFactory.create(event=cls.event).name
		cls.free = cls.create_booking(cls.event, ticket_type=free_type, payment_status="Unpaid")
		other_type = EventTicketTypeFactory.create(
			event=cls.other_event, prices=[{"currency": "INR", "price": TICKET_PRICE}]
		).name
		cls.elsewhere = cls.create_booking(cls.other_event, ticket_type=other_type)

	@classmethod
	def create_booking(cls, event, attendees=1, ticket_type=None, submit=True, **overrides):
		ticket_type = ticket_type or cls.ticket_type
		booking = EventBookingFactory.create(
			event=event,
			attendees=[
				{
					"ticket_type": ticket_type,
					"first_name": f"Buyer {index}",
					"email": f"buyer-{index}@example.com",
				}
				for index in range(attendees)
			],
			**{"payment_status": "Paid", **overrides},
		)
		if submit:
			booking.submit()
		return booking

	def transactions_as(self, user: str, **arguments):
		with self.set_user(user):
			return get_event_transactions(self.event, **arguments)

	def names_as(self, user: str | None = None, **arguments) -> set[str]:
		page = self.transactions_as(user or self.owner, **arguments)
		return {row.name for row in page.transactions}


class TestTransactionsAccess(TransactionsTestCase):
	def endpoints(self):
		return {
			"list": lambda: get_event_transactions(self.event),
			"detail": lambda: get_transaction(self.event, self.paid.name),
			"summary": lambda: get_transaction_summary(self.event),
		}

	def test_team_write_roles_and_ticketing_collaborators_are_allowed(self):
		for user in (self.owner, self.admin, self.manager, self.ticketing_viewer, "Administrator"):
			for endpoint, call in self.endpoints().items():
				with self.subTest(user=user, endpoint=endpoint), self.set_user(user):
					call()

	def test_everyone_else_is_refused(self):
		refused = (
			self.viewer,
			self.frontdesk,
			self.other_manager,
			self.guests_viewer,
			self.attendee,
			"Guest",
		)
		for user in refused:
			for endpoint, call in self.endpoints().items():
				with self.subTest(user=user, endpoint=endpoint), self.set_user(user):
					with self.assertRaises(CannotManageEvent):
						call()

	def test_event_access_reports_the_transactions_page(self):
		for user, expected in ((self.manager, "View"), (self.ticketing_viewer, "View"), (self.viewer, None)):
			with self.subTest(user=user), self.set_user(user):
				self.assertEqual(get_event_access(self.event)["transactions"], expected)

	def test_a_booking_of_another_event_is_not_found(self):
		with self.set_user(self.owner), self.assertRaises(TransactionNotFound):
			get_transaction(self.event, self.elsewhere.name)

	def test_a_booking_that_is_not_a_transaction_is_not_found(self):
		with self.set_user(self.owner), self.assertRaises(TransactionNotFound):
			get_transaction(self.event, self.free.name)

	def test_a_filter_off_the_list_is_refused(self):
		with self.assertRaises(InvalidFilter):
			self.transactions_as(self.owner, filters=json.dumps([["buyer_phone", "like", "9"]]))


class TestTransactionRows(TransactionsTestCase):
	def test_lists_paid_and_verification_pending_bookings_only(self):
		page = self.transactions_as(self.owner)

		self.assertEqual({row.name for row in page.transactions}, {self.paid.name, self.pending.name})
		self.assertEqual((page.total, page.matched), (2, 2))
		self.assertEqual(page.title, "Money Event")
		self.assertEqual(page.currencies, ["INR"])

	def test_row_carries_the_payment(self):
		row = next(row for row in self.transactions_as(self.owner).transactions if row.name == self.paid.name)

		self.assertEqual(row.payment_id, self.payment.payment_id)
		self.assertEqual(row.payment_method, self.gateway)
		self.assertEqual(row.tickets, 2)
		self.assertEqual(row.total_amount, 2 * TICKET_PRICE)

	def test_offline_row_names_the_method_the_buyer_picked(self):
		row = next(
			row for row in self.transactions_as(self.owner).transactions if row.name == self.pending.name
		)

		self.assertEqual(row.payment_method, "Bank Transfer")

	def test_search_by_payment_id_finds_the_booking(self):
		self.assertEqual(self.names_as(search=self.payment.payment_id), {self.paid.name})

	def test_search_treats_wildcards_literally(self):
		self.assertEqual(self.names_as(search="%"), set())

	def test_filters_narrow_the_rows(self):
		by_status = json.dumps([["payment_status", "in", ["Verification Pending"]]])
		by_method = json.dumps([["payment_method", "in", [self.gateway]]])

		self.assertEqual(self.names_as(filters=by_status), {self.pending.name})
		self.assertEqual(self.names_as(filters=by_method), {self.paid.name})

	def test_ticket_type_filter_reads_through_attendees(self):
		chosen = json.dumps([["ticket_type", "in", [str(self.ticket_type)]]])
		excluded = json.dumps([["ticket_type", "not in", [str(self.ticket_type)]]])

		self.assertEqual(self.names_as(filters=chosen), {self.paid.name, self.pending.name})
		self.assertEqual(self.names_as(filters=excluded), set())

	def test_creation_filter_matches_the_whole_day(self):
		today = str(frappe.utils.getdate(self.paid.creation))

		self.assertIn(self.paid.name, self.names_as(filters=json.dumps([["creation", "=", today]])))
		self.assertEqual(self.names_as(filters=json.dumps([["creation", ">", today]])), set())

	def test_name_narrows_to_one_booking(self):
		self.assertEqual(self.names_as(name=self.pending.name), {self.pending.name})

	def test_pages_in_creation_order(self):
		first = self.transactions_as(self.owner, order="asc", limit=1)

		self.assertEqual([row.name for row in first.transactions], [self.paid.name])
		self.assertTrue(first.has_next_page)


class TestTransactionDetail(TransactionsTestCase):
	def detail(self, booking: str):
		with self.set_user(self.owner):
			return get_transaction(self.event, booking)

	def test_returns_the_tickets_and_line_items(self):
		detail = self.detail(self.paid.name)

		self.assertEqual(len(detail.tickets), 2)
		self.assertEqual({ticket.ticket_type for ticket in detail.tickets}, {"General"})
		self.assertFalse(any(ticket.checked_in for ticket in detail.tickets))
		self.assertEqual(
			[item.attendee_email for item in detail.line_items],
			["buyer-0@example.com", "buyer-1@example.com"],
		)

	def test_returns_payments_and_amounts(self):
		detail = self.detail(self.paid.name)

		self.assertEqual([payment.payment_id for payment in detail.payments], [self.payment.payment_id])
		self.assertTrue(detail.payments[0].payment_received)
		self.assertEqual(detail.amounts.total_amount, 2 * TICKET_PRICE)
		self.assertEqual(detail.amounts.net_received, 2 * TICKET_PRICE)
		self.assertEqual(detail.refunds, [])

	def test_payload_serializes(self):
		payload = self.detail(self.pending.name).__json__()

		self.assertEqual(payload["payment_method"], "Bank Transfer")
		self.assertEqual(payload["tickets"], [])


class TestTransactionSummary(TransactionsTestCase):
	def summary(self):
		with self.set_user(self.owner):
			return get_transaction_summary(self.event)

	def test_paid_totals_match_the_paid_rows(self):
		rows = self.transactions_as(self.owner).transactions
		paid_total = sum(row.total_amount for row in rows if row.payment_status == "Paid")

		inr = self.summary().currencies[0]

		self.assertEqual((inr.currency, inr.collected, inr.bookings, inr.tickets), ("INR", paid_total, 1, 2))
		self.assertEqual(inr.net, paid_total)
		self.assertEqual(inr.average_order_value, paid_total)

	def test_pending_verification_is_counted_apart(self):
		pending = self.summary().pending_verification

		self.assertEqual(
			[(row.currency, row.bookings, row.amount) for row in pending], [("INR", 1, TICKET_PRICE)]
		)

	def test_groups_paid_bookings_by_payment_method(self):
		methods = self.summary().by_payment_method

		self.assertEqual(
			[(row.payment_method, row.bookings, row.amount) for row in methods],
			[(self.gateway, 1, 2 * TICKET_PRICE)],
		)


class TestPaymentDoctypePermissions(TransactionsTestCase):
	def can_read(self, user: str, doctype: str, name: str) -> bool:
		with self.set_user(user):
			return frappe.has_permission(doctype, "read", doc=name)

	def test_event_payment_follows_the_transactions_rule(self):
		payment = self.payment.name
		self.assertTrue(self.can_read(self.manager, "Event Payment", payment))
		self.assertTrue(self.can_read(self.ticketing_editor, "Event Payment", payment))
		self.assertFalse(self.can_read(self.frontdesk, "Event Payment", payment))
		self.assertFalse(self.can_read(self.guests_editor, "Event Payment", payment))
		self.assertFalse(self.can_read(self.guests_viewer, "Event Payment", payment))

	def test_guests_editor_still_reads_the_booking(self):
		self.assertTrue(self.can_read(self.guests_editor, "Event Booking", self.paid.name))
