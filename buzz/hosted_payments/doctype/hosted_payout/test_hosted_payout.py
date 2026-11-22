import frappe
from bwh_payments import testing as payment_testing
from frappe.utils import add_days, today

from buzz.api.hosted_payments import create_order, refund
from buzz.tests.base_test_cases import HostedPaymentsTestCase
from buzz.tests.factories import HostedPayoutFactory


class TestHostedPayout(HostedPaymentsTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		settings = frappe.get_doc("Buzz Settings")
		settings.hosted_payment_fallback_rate = 5
		settings.set(
			"hosted_payment_rates",
			[{"payment_method": "upi", "rate": 3.3}, {"payment_method": "card_credit", "rate": 4.4}],
		)
		settings.save()

	def setUp(self):
		super().setUp()
		# Rollback is per class, so each test undoes its own payments.
		frappe.db.savepoint("hosted_payout_test")
		self.addCleanup(frappe.db.rollback, save_point="hosted_payout_test")

	def paid_order(self, amount: float, payment_method: str = "upi") -> str:
		with self.set_user(self.integration):
			order_id = create_order(**self.order_values(amount=amount)).order_id
		payment_testing.pay(
			frappe.db.get_value("Hosted Payment", order_id, "payment_request"), payment_method
		)
		return order_id

	def refund(self, order_id: str, amount: float) -> None:
		with self.set_user(self.integration):
			refund(order_id, amount)

	def payout_with_payments(self, **overrides):
		payout = HostedPayoutFactory.create(team=self.team, **overrides)
		payout.get_payments()
		payout.save()
		return payout

	def line_values(self, payout) -> list[tuple]:
		fields = ("hosted_payment", "payment_method", "rate", "gross", "refunded", "commission", "net")
		return [tuple(line.get(field) for field in fields) for line in payout.lines]

	def test_upi_payment_is_charged_the_upi_rate(self):
		order_id = self.paid_order(1000, "upi")
		payout = self.payout_with_payments()
		self.assertEqual(self.line_values(payout), [(order_id, "upi", 3.3, 1000, 0, 33, 967)])

	def test_credit_card_payment_is_charged_the_credit_card_rate(self):
		order_id = self.paid_order(1000, "card_credit")
		payout = self.payout_with_payments()
		self.assertEqual(self.line_values(payout), [(order_id, "card_credit", 4.4, 1000, 0, 44, 956)])

	def test_method_without_a_rate_is_charged_the_fallback_rate(self):
		order_id = self.paid_order(1000, "netbanking")
		payout = self.payout_with_payments()
		self.assertEqual(self.line_values(payout), [(order_id, "netbanking", 5, 1000, 0, 50, 950)])

	def test_commission_is_charged_on_gross_and_kept_on_a_refund(self):
		order_id = self.paid_order(1000, "upi")
		self.refund(order_id, 400)
		payout = self.payout_with_payments()
		self.assertEqual(self.line_values(payout), [(order_id, "upi", 3.3, 1000, 400, 33, 567)])

	def test_totals_add_up_the_lines(self):
		self.paid_order(1000, "upi")
		self.refund(self.paid_order(500, "card_credit"), 100)
		payout = self.payout_with_payments()
		totals = (payout.total_gross, payout.total_refunded, payout.total_commission, payout.total_net)
		self.assertEqual(totals, (1500, 100, 55, 1345))

	def submit(self, payout, transfer_reference: str = "UTR-1001"):
		payout.transfer_reference = transfer_reference
		payout.submit()
		return payout

	def payout_of(self, order_id: str) -> str | None:
		return frappe.db.get_value("Hosted Payment", order_id, "payout")

	def test_submit_settles_the_payments(self):
		order_id = self.paid_order(1000)
		payout = self.submit(self.payout_with_payments())
		self.assertEqual(self.payout_of(order_id), payout.name)

	def test_transfer_reference_is_required_to_submit(self):
		order_id = self.paid_order(1000)
		payout = self.payout_with_payments()
		with self.assertRaises(frappe.ValidationError):
			self.submit(payout, transfer_reference="")
		self.assertIsNone(self.payout_of(order_id))
