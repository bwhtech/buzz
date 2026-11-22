from unittest.mock import patch

import frappe
from bwh_payments import testing as payment_testing
from frappe.tests import IntegrationTestCase

from buzz.payments import get_payment_link_for_booking
from buzz.tests.base_test_cases import make_payment_gateway
from buzz.tests.factories import BuzzEventFactory, EventBookingFactory, EventTicketTypeFactory
from buzz.tests.sessions import Session, in_session, overlap
from buzz.ticketing.doctype.event_booking_refund.event_booking_refund import EventBookingRefund


def refund(booking: str, amount: float) -> str:
	with patch("frappe.sendmail"):
		return frappe.get_doc("Event Booking", booking).refund(amount=amount)


def sync_refunds(booking: str):
	with patch("frappe.sendmail"):
		frappe.get_doc("Event Booking", booking).sync_refunds()


class TestOverlappingBookingRefunds(IntegrationTestCase):
	"""A paid ₹1,000 booking refunded by requests of their own, which commit as real ones do.

	Each refund pauses after its Event Booking Refund is inserted, with the locks it holds by then.
	"""

	def setUp(self):
		payment_testing.reset()
		self.booking, self.payment_request = in_session(self.paid_booking)
		self.addCleanup(in_session, self.delete_fixtures)

	def paid_booking(self):
		event = BuzzEventFactory.create(payment_gateways=[{"payment_gateway": make_payment_gateway()}]).name
		ticket_type = EventTicketTypeFactory.create(event=event, prices=[{"currency": "INR", "price": 1000}])
		attendee = {"ticket_type": ticket_type.name, "first_name": "Riya", "email": "riya@example.com"}
		booking = EventBookingFactory.create(event=event, attendees=[attendee]).name
		get_payment_link_for_booking(booking)
		payment_request = frappe.db.get_value(
			"Event Payment", {"reference_docname": booking}, "payment_request"
		)
		with patch("frappe.sendmail"):
			payment_testing.pay(payment_request)
		return booking, payment_request

	def delete_fixtures(self):
		frappe.db.delete("Gateway Refund", {"payment_request": self.payment_request})
		frappe.db.delete("Gateway Payment Request", self.payment_request)
		frappe.db.delete("Event Payment", {"reference_docname": self.booking})
		for doctype in ("Event Booking Refund", "Event Ticket"):
			frappe.db.delete(doctype, {"booking": self.booking})
		frappe.db.delete("Event Booking Attendee", {"parent": self.booking})
		frappe.db.delete("Event Booking", self.booking)

	def overlap_refunds(self, inner: Session) -> Session:
		outer = Session(lambda: refund(self.booking, 300))
		overlap(outer, EventBookingRefund, "on_update", inner)
		return outer

	def assert_no_deadlock(self, *sessions: Session):
		self.assertEqual([session.error for session in sessions], [None] * len(sessions))

	def refunds(self) -> list:
		return in_session(
			lambda: frappe.get_all(
				"Event Booking Refund", {"booking": self.booking}, ["amount", "status"], order_by="amount"
			)
		)

	def test_two_overlapping_refunds_both_go_through(self):
		inner = Session(lambda: refund(self.booking, 200))
		outer = self.overlap_refunds(inner)

		self.assert_no_deadlock(outer, inner)
		self.assertEqual(
			[(r.amount, r.status) for r in self.refunds()], [(200, "Processed"), (300, "Processed")]
		)

	def test_a_refund_overlapping_a_settling_refund_waits_for_it(self):
		payment_testing.set_next_refund_status("Pending")
		in_session(lambda: refund(self.booking, 200))
		in_session(self.settle_at_the_gateway)
		payment_testing.set_next_refund_status("Processed")
		settling = Session(lambda: sync_refunds(self.booking))

		outer = self.overlap_refunds(settling)

		self.assert_no_deadlock(outer, settling)
		self.assertEqual(
			[(r.amount, r.status) for r in self.refunds()], [(200, "Processed"), (300, "Processed")]
		)

	def settle_at_the_gateway(self):
		pending = frappe.db.get_value("Gateway Refund", {"payment_request": self.payment_request})
		payment_testing.set_refund_status(pending, "Processed")
