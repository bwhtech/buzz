import frappe
from frappe.tests import IntegrationTestCase

from buzz.patches.move_payments_to_bwh_payments import PaymentHistoryMigration
from buzz.tests.base_test_cases import make_payment_gateway
from buzz.tests.factories import EventBookingFactory, EventBookingRefundFactory, EventPaymentFactory


class TestMovePaymentsToBwhPayments(IntegrationTestCase):
	def setUp(self):
		self.gateway = make_payment_gateway()
		self.booking = EventBookingFactory.create()
		self.booking.submit()
		self.paid = self.make_legacy_payment(
			"received", payment_id="pay_legacy_paid", order_id="order_legacy_paid", amount=1000
		)
		self.unpaid = self.make_legacy_payment(amount=1000)
		self.refund = EventBookingRefundFactory.create(
			booking=self.booking.name,
			payment=self.paid.name,
			refund_id="rfnd_legacy_1",
			status="Processed",
			amount=400,
			currency="INR",
		)

	def tearDown(self):
		# The migration reads every payment on the site, so one test's rows must not reach the next.
		frappe.db.rollback()

	def make_legacy_payment(self, *traits, **values):
		return EventPaymentFactory.create(
			*traits,
			reference_doctype="Event Booking",
			reference_docname=self.booking.name,
			payment_gateway=self.gateway,
			currency="INR",
			**values,
		)

	def get_payment_request(self, payment):
		name = frappe.db.get_value("Event Payment", payment.name, "payment_request")
		return frappe.get_doc("Gateway Payment Request", name)

	def test_a_received_payment_becomes_a_settled_payment_request_with_its_refunds(self):
		PaymentHistoryMigration().run()

		payment_request = self.get_payment_request(self.paid)
		self.assertEqual(
			(payment_request.status, payment_request.amount, payment_request.refund_amount),
			("Partially Refunded", 1000, 400),
		)
		self.assertEqual(
			(payment_request.order_ref, payment_request.gateway_transaction_ref, payment_request.gateway),
			("order_legacy_paid", "pay_legacy_paid", self.gateway),
		)
		self.assertEqual(
			(payment_request.ref_doctype, payment_request.ref_docname), ("Event Booking", self.booking.name)
		)

	def test_an_unpaid_payment_is_kept_as_an_expired_payment_request(self):
		PaymentHistoryMigration().run()

		payment_request = self.get_payment_request(self.unpaid)
		self.assertEqual(payment_request.status, "Expired")
		self.assertEqual(payment_request.order_ref, f"legacy-{self.unpaid.name}")

	def test_a_refund_is_linked_to_its_gateway_refund_and_keeps_its_own_record(self):
		PaymentHistoryMigration().run()

		self.refund.reload()
		gateway_refund = frappe.get_doc("Gateway Refund", self.refund.gateway_refund)
		self.assertEqual(
			(
				gateway_refund.refund_id,
				gateway_refund.status,
				gateway_refund.amount,
				gateway_refund.reference,
			),
			("rfnd_legacy_1", "Processed", 400, self.refund.name),
		)
		self.assertEqual((self.refund.refund_id, self.refund.status), ("rfnd_legacy_1", "Processed"))

	def test_the_legacy_payment_fields_are_left_as_they_were(self):
		PaymentHistoryMigration().run()

		self.assertEqual(
			frappe.db.get_value(
				"Event Payment", self.paid.name, ["payment_received", "payment_id", "order_id"], as_dict=True
			),
			{"payment_received": 1, "payment_id": "pay_legacy_paid", "order_id": "order_legacy_paid"},
		)

	def test_running_it_again_creates_nothing_new(self):
		PaymentHistoryMigration().run()
		payment_requests = frappe.db.count("Gateway Payment Request")
		gateway_refunds = frappe.db.count("Gateway Refund")

		PaymentHistoryMigration().run()

		self.assertEqual(frappe.db.count("Gateway Payment Request"), payment_requests)
		self.assertEqual(frappe.db.count("Gateway Refund"), gateway_refunds)

	def test_a_gateway_that_no_longer_exists_is_kept_for_history_but_disabled(self):
		retired = self.make_legacy_payment("received", amount=10)
		# Set past the Link check: the gateway was deleted along with frappe/payments' record of it.
		frappe.db.set_value("Event Payment", retired.name, "payment_gateway", "Retired Gateway")

		PaymentHistoryMigration().run()

		self.assertEqual(frappe.db.get_value("Payment Gateway Profile", "Retired Gateway", "enabled"), 0)
		self.assertEqual(self.get_payment_request(retired).gateway, "Retired Gateway")

	def test_importing_settles_nothing_again(self):
		PaymentHistoryMigration().run()

		self.assertEqual(frappe.db.count("Ticket Cancellation Request", {"booking": self.booking.name}), 0)
		self.assertEqual(frappe.db.get_value("Event Booking", self.booking.name, "docstatus"), 1)

	def test_a_payment_for_a_deleted_booking_is_skipped_and_logged_without_stopping_the_rest(self):
		orphan_booking = EventBookingFactory.create()
		orphan = EventPaymentFactory.create(
			"received",
			reference_doctype="Event Booking",
			reference_docname=orphan_booking.name,
			payment_gateway=self.gateway,
			currency="INR",
			amount=10,
		)
		frappe.db.delete("Event Booking", orphan_booking.name)
		errors_before = frappe.db.count("Error Log")

		PaymentHistoryMigration().run()

		self.assertIsNone(frappe.db.get_value("Event Payment", orphan.name, "payment_request"))
		self.assertTrue(frappe.db.get_value("Event Payment", self.paid.name, "payment_request"))
		self.assertEqual(frappe.db.count("Error Log"), errors_before + 1)
