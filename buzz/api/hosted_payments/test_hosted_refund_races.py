import frappe
from bwh_payments import testing as payment_testing
from bwh_payments.services.razorpay.stub import (  # nosemgrep: frappe-monkey-patching-not-allowed
	StubRazorpayClient,
)

from buzz.api.hosted_payments import create_order, refund
from buzz.api.hosted_payments.exceptions import RefundExceedsBalance
from buzz.tests.base_test_cases import HostedPaymentsTestCase
from buzz.tests.factories import HostedPayoutFactory


class HubRefundRaceTestCase(HostedPaymentsTestCase):
	"""Another worker commits a refund after this transaction took its snapshot.

	One test per class: the class transaction keeps every lock its tests take, and the other worker would
	wait on them.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.reserved_elsewhere = []

	@classmethod
	def tearDownClass(cls):
		super().tearDownClass()
		# The class rollback runs later, so this one frees the locks the other worker waits on.
		frappe.db.rollback()
		for name in cls.reserved_elsewhere:
			payment_testing.commit_elsewhere("delete from `tabGateway Refund` where name = %s", (name,))

	def setUp(self):
		super().setUp()
		with self.set_user(self.integration):
			self.order_id = create_order(**self.order_values(amount=1000)).order_id
		self.payment_request = frappe.db.get_value("Hosted Payment", self.order_id, "payment_request")
		payment_testing.pay(self.payment_request)

	def reserve_elsewhere(self, amount: float, reference: str | None = None) -> str:
		name = payment_testing.reserve_refund_elsewhere(self.payment_request, amount, reference)
		self.reserved_elsewhere.append(name)
		return name

	def refund(self, amount: float, idempotency_key: str):
		with self.set_user(self.integration):
			return refund(self.order_id, amount, idempotency_key)


class TestRefundReservedByAnotherWorker(HubRefundRaceTestCase):
	def test_counts_against_the_balance(self):
		self.reserve_elsewhere(700)
		with self.assertRaises(RefundExceedsBalance):
			self.refund(700, frappe.generate_hash())
		self.assertEqual(StubRazorpayClient.created_refunds, [])


class TestRefundRetriedWhileAnotherWorkerMadeIt(HubRefundRaceTestCase):
	def test_returns_the_refund_the_other_worker_made(self):
		name = self.reserve_elsewhere(200, reference="PRO-RFND-RACE")
		retry = self.refund(200, "PRO-RFND-RACE")
		self.assertEqual((retry.refund_id, retry.status, retry.amount), (name, "Pending", 200))
		self.assertEqual(StubRazorpayClient.created_refunds, [])


class TestPendingRefundAfterAnotherWorkerSettledOne(HubRefundRaceTestCase):
	def test_the_mirror_and_the_payout_count_the_settled_refund(self):
		settled = self.reserve_elsewhere(300)
		payment_testing.commit_elsewhere(
			"update `tabGateway Refund` set status = 'Processed' where name = %s", (settled,)
		)
		payment_testing.set_next_refund_status("Pending")

		self.assertEqual(self.refund(200, frappe.generate_hash()).status, "Pending")

		self.assertEqual(frappe.db.get_value("Hosted Payment", self.order_id, "refunded_amount"), 300)
		payout = HostedPayoutFactory.create(team=self.team)
		payout.get_payments()
		[line] = [line for line in payout.lines if line.hosted_payment == self.order_id]
		self.assertEqual(line.refunded, 300)
