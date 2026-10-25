import frappe

from buzz.api.booking.approvals import (
	approve_bookings,
	decline_bookings,
	get_affected_requests,
	get_pending_bookings,
	set_approval,
	withdraw_booking,
)
from buzz.api.booking.exceptions import BookingNotPending, CannotWithdrawBooking
from buzz.api.booking.services import get_booking_access_token
from buzz.api.events.exceptions import CannotManageEvent
from buzz.tests.base_test_cases import ApprovalTestCase
from buzz.tests.factories import BuzzEventFactory, EventTicketTypeFactory, UserFactory


class TestApprovalEndpoints(ApprovalTestCase):
	def setUp(self):
		super().setUp()
		self.organizer = self.make_organizer()
		self.guest_one = UserFactory.create_once("approval-guest-one@example.com").name
		self.guest_two = UserFactory.create_once("approval-guest-two@example.com").name

	def event_name(self) -> str:
		return str(self.event.name)

	def status_of(self, booking: str) -> tuple:
		return frappe.db.get_value("Event Booking", booking, ["docstatus", "status"])

	def test_pending_list_is_oldest_first_with_the_request_details(self):
		first = self.request_to_join(self.guest_one)
		second = self.request_to_join(self.guest_two)

		with self.set_user(self.organizer):
			payload = get_pending_bookings(self.event_name()).__json__()

		self.assertEqual(payload["total"], 2)
		self.assertEqual([row["name"] for row in payload["bookings"]], [first, second])
		row = payload["bookings"][0]
		self.assertEqual(
			set(row),
			{
				"name",
				"buyer_name",
				"buyer_email",
				"requested_at",
				"previously_declined",
				"attendees",
				"answers",
			},
		)
		self.assertEqual(row["attendees"][0]["ticket_type"], self.approval_ticket_type.title)
		self.assertFalse(row["previously_declined"])

	def test_a_new_request_after_a_decline_is_tagged(self):
		declined = self.request_to_join(self.guest_one)
		with self.set_user(self.organizer):
			decline_bookings(self.event_name(), [declined], None)
		self.request_to_join(self.guest_one)

		with self.set_user(self.organizer):
			[row] = get_pending_bookings(self.event_name()).bookings

		self.assertTrue(row.previously_declined)

	def test_approve_reports_each_booking(self):
		fits = self.request_to_join(self.guest_one)
		self.approval_ticket_type.max_tickets_available = 1
		self.approval_ticket_type.save()
		second = self.request_to_join(self.guest_two)

		with self.set_user(self.organizer):
			result = approve_bookings(self.event_name(), [fits, second])

		self.assertEqual(result.approved, [fits])
		self.assertEqual([failure.booking for failure in result.failed], [second])
		self.assertEqual(self.status_of(fits), (1, "Confirmed"))
		self.assertEqual(self.status_of(second), (0, "Approval Pending"))

	def test_second_approval_of_the_same_request_fails_cleanly(self):
		booking = self.request_to_join(self.guest_one)
		with self.set_user(self.organizer):
			approve_bookings(self.event_name(), [booking])
			result = approve_bookings(self.event_name(), [booking])

		self.assertEqual([failure.booking for failure in result.failed], [booking])

	def test_decline_stores_the_message(self):
		booking = self.request_to_join(self.guest_one)

		with self.set_user(self.organizer):
			result = decline_bookings(self.event_name(), [booking], "  Not this time  ")

		self.assertEqual(result.declined, [booking])
		self.assertEqual(self.status_of(booking), (2, "Rejected"))
		self.assertEqual(frappe.db.get_value("Event Booking", booking, "rejection_reason"), "Not this time")

	def test_a_booking_of_another_event_cannot_be_decided_here(self):
		booking = self.request_to_join(self.guest_one)
		other_event = str(BuzzEventFactory.create(team=self.event.team).name)

		with self.set_user(self.organizer):
			result = approve_bookings(other_event, [booking])

		self.assertEqual([failure.booking for failure in result.failed], [booking])

	def test_set_approval_keep_leaves_requests_pending(self):
		booking = self.request_to_join(self.guest_one)
		with self.set_user(self.organizer):
			self.assertEqual(
				get_affected_requests(self.event_name(), str(self.approval_ticket_type.name)).count, 1
			)
			result = set_approval(self.event_name(), False, str(self.approval_ticket_type.name))

		self.assertEqual((result.approved, result.failed, result.declined), (0, 0, 0))
		self.approval_ticket_type.reload()
		self.assertEqual(self.approval_ticket_type.requires_approval, 0)
		self.assertEqual(self.status_of(booking), (0, "Approval Pending"))

	def test_set_approval_approve_reports_a_partial_result(self):
		self.approval_ticket_type.max_tickets_available = 1
		self.approval_ticket_type.save()
		self.request_to_join(self.guest_one)
		self.request_to_join(self.guest_two)

		with self.set_user(self.organizer):
			result = set_approval(self.event_name(), False, str(self.approval_ticket_type.name), "approve")

		self.assertEqual((result.approved, result.failed, result.declined), (1, 1, 0))

	def test_set_approval_decline_declines_the_released_requests(self):
		booking = self.request_to_join(self.guest_one)

		with self.set_user(self.organizer):
			result = set_approval(self.event_name(), False, str(self.approval_ticket_type.name), "decline")

		self.assertEqual(result.declined, 1)
		self.assertEqual(self.status_of(booking), (2, "Rejected"))

	def test_turning_off_one_ticket_type_leaves_bookings_that_need_another_pending(self):
		other = EventTicketTypeFactory.create("requires_approval", event=self.event.name)
		mixed = self.request_to_join(self.guest_one, self.approval_ticket_type.name, other.name)
		single = self.request_to_join(self.guest_two, self.approval_ticket_type.name)

		with self.set_user(self.organizer):
			result = set_approval(self.event_name(), False, str(self.approval_ticket_type.name), "approve")

		self.assertEqual(result.approved, 1)
		self.assertEqual(self.status_of(mixed), (0, "Approval Pending"))
		self.assertEqual(self.status_of(single), (1, "Confirmed"))

	def test_turning_off_event_wide_approval_keeps_ticket_type_requests_pending(self):
		self.set_event({"requires_approval": 1})
		wide = self.request_to_join(self.guest_one, self.free_ticket_type.name)
		by_ticket = self.request_to_join(self.guest_two, self.approval_ticket_type.name)

		with self.set_user(self.organizer):
			self.assertEqual(get_affected_requests(self.event_name()).count, 1)
			set_approval(self.event_name(), False, None, "approve")

		self.assertEqual(self.status_of(wide), (1, "Confirmed"))
		self.assertEqual(self.status_of(by_ticket), (0, "Approval Pending"))
		self.assertEqual(frappe.db.get_value("Buzz Event", self.event.name, "requires_approval"), 0)

	def test_every_organizer_endpoint_refuses_outsiders_and_guests(self):
		calls = [
			lambda: get_pending_bookings(self.event_name()),
			lambda: approve_bookings(self.event_name(), []),
			lambda: decline_bookings(self.event_name(), [], None),
			lambda: get_affected_requests(self.event_name()),
			lambda: set_approval(self.event_name(), False),
		]
		for user in (self.outsider, "Guest"):
			for call in calls:
				with self.set_user(user), self.assertRaises(CannotManageEvent):
					call()

	def test_set_approval_needs_ticketing_write(self):
		frontdesk = self.make_organizer("Frontdesk")

		with self.set_user(frontdesk), self.assertRaises(CannotManageEvent):
			set_approval(self.event_name(), False, str(self.approval_ticket_type.name))

		self.approval_ticket_type.reload()
		self.assertEqual(self.approval_ticket_type.requires_approval, 1)

	def test_decline_skips_requests_that_are_no_longer_pending(self):
		decided = self.request_to_join(self.guest_one)
		waiting = self.request_to_join(self.guest_two)
		frappe.get_doc("Event Booking", decided).decline_request()

		with self.set_user(self.organizer):
			result = decline_bookings(self.event_name(), [decided, waiting], None)

		self.assertEqual(result.declined, [waiting])

	def test_pending_list_is_capped_but_reports_the_total(self):
		self.request_to_join(self.guest_one)
		self.request_to_join(self.guest_two)

		with self.set_user(self.organizer):
			payload = get_pending_bookings(self.event_name(), limit=1)

		self.assertEqual((payload.total, len(payload.bookings)), (2, 1))

	def test_withdrawing_an_unknown_booking_looks_like_a_refusal(self):
		with self.set_user("Guest"), self.assertRaises(CannotWithdrawBooking):
			withdraw_booking("no-such-booking")

	def test_a_viewer_cannot_decide_requests(self):
		viewer = self.make_organizer("Viewer")

		with self.set_user(viewer), self.assertRaises(CannotManageEvent):
			approve_bookings(self.event_name(), [])


class TestWithdrawBooking(ApprovalTestCase):
	def test_the_owner_withdraws_without_an_email(self):
		booking = self.request_to_join()
		emails = frappe.db.count("Email Queue", {"reference_name": booking})

		with self.set_user(self.booker):
			withdraw_booking(booking)

		self.assertEqual(
			frappe.db.get_value("Event Booking", booking, ["docstatus", "status"]), (2, "Withdrawn")
		)
		self.assertEqual(frappe.db.count("Email Queue", {"reference_name": booking}), emails)

	def test_a_guest_with_the_access_token_withdraws(self):
		booking = self.request_to_join()

		with self.set_user("Guest"):
			withdraw_booking(booking, get_booking_access_token(booking))

		self.assertEqual(frappe.db.get_value("Event Booking", booking, "status"), "Withdrawn")

	def test_a_stranger_is_refused(self):
		booking = self.request_to_join()

		for user, token in ((self.outsider, None), ("Guest", "wrong")):
			with self.set_user(user), self.assertRaises(CannotWithdrawBooking):
				withdraw_booking(booking, token)

	def test_a_decided_request_cannot_be_withdrawn(self):
		booking = frappe.get_doc("Event Booking", self.request_to_join())
		booking.decline_request()

		with self.set_user(self.booker), self.assertRaises(BookingNotPending):
			withdraw_booking(booking.name)
