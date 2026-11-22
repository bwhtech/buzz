import frappe
from bwh_payments import testing as payment_testing
from frappe.utils import add_days, now_datetime, today

from buzz.api.hosted_payments import create_order, refund
from buzz.tests.base_test_cases import HostedPaymentsTestCase
from buzz.tests.factories import BuzzTeamFactory, HostedPaymentFactory, HostedPayoutFactory


class HostedPayoutTestCase(HostedPaymentsTestCase):
	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.clear_document_cache, "Buzz Settings", "Buzz Settings")
		# Rollback is per class, so each test undoes its own payments and rates.
		frappe.db.savepoint("hosted_payout_test")
		self.addCleanup(frappe.db.rollback, save_point="hosted_payout_test")
		self.set_rates({"upi": 3.3, "card_credit": 4.4}, fallback_rate=5)

	def set_rates(self, rates: dict[str, float], fallback_rate: float) -> None:
		settings = frappe.get_single("Buzz Settings")
		settings.hosted_payment_fallback_rate = fallback_rate
		rows = [{"payment_method": method, "rate": rate} for method, rate in rates.items()]
		settings.set("hosted_payment_rates", rows)
		settings.save()

	def paid_order(self, amount: float, payment_method: str = "upi") -> str:
		with self.set_user(self.integration):
			order_id = create_order(**self.order_values(amount=amount)).order_id
		payment_testing.pay(
			frappe.db.get_value("Hosted Payment", order_id, "payment_request"), payment_method
		)
		return order_id

	def refund(self, order_id: str, amount: float) -> None:
		with self.set_user(self.integration):
			refund(order_id, amount, frappe.generate_hash())

	def payout_with_payments(self, **overrides):
		payout = HostedPayoutFactory.create(team=self.team, **overrides)
		payout.get_payments()
		return payout

	def line_values(self, payout) -> list[tuple]:
		fields = ("hosted_payment", "payment_method", "rate", "gross", "refunded", "commission", "net")
		return [tuple(line.get(field) for field in fields) for line in payout.lines]

	def settled_payment(self, currency: str, amount: float) -> str:
		return HostedPaymentFactory.create("paid", team=self.team, currency=currency, amount=amount).name

	def submit(self, payout, transfer_reference: str = "UTR-1001"):
		payout.transfer_reference = transfer_reference
		payout.submit()
		return payout

	def payout_of(self, order_id: str) -> str | None:
		return frappe.db.get_value("Hosted Payment", order_id, "payout")


class TestHostedPayout(HostedPayoutTestCase):
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

	def test_unknown_method_is_charged_the_fallback_rate(self):
		order_id = self.paid_order(1000, "upi")
		frappe.db.set_value("Hosted Payment", order_id, "payment_method", "bank_transfer")
		payout = self.payout_with_payments()
		self.assertEqual(self.line_values(payout), [(order_id, "bank_transfer", 5, 1000, 0, 50, 950)])

	def test_rate_for_a_method_outside_the_list_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.set_rates({"UPI": 3.3}, fallback_rate=5)

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

	def test_totals_are_rounded_to_the_currency(self):
		self.paid_order(100.1, "upi")
		self.paid_order(200.2, "upi")
		payout = self.payout_with_payments()
		totals = (payout.total_gross, payout.total_refunded, payout.total_commission, payout.total_net)
		self.assertEqual(totals, (300.3, 0, 9.91, 290.39))

	def test_three_decimal_currency_keeps_its_third_decimal(self):
		order_id = self.settled_payment("KWD", 1.234)
		payout = self.payout_with_payments(currency="KWD")
		self.assertEqual(self.line_values(payout), [(order_id, "upi", 3.3, 1.234, 0, 0.041, 1.193)])

	def test_three_decimal_refund_after_settlement_is_carried_forward(self):
		order_id = self.settled_payment("KWD", 10)
		self.submit(self.payout_with_payments(currency="KWD"))
		frappe.db.set_value("Hosted Payment", order_id, "refunded_amount", 0.004)
		payout = self.payout_with_payments(currency="KWD")
		self.assertEqual(self.line_values(payout), [(order_id, "upi", 0, 0, 0.004, 0, -0.004)])

	def test_zero_decimal_currency_rounds_to_whole_units(self):
		order_id = self.settled_payment("JPY", 1001)
		payout = self.payout_with_payments(currency="JPY")
		self.assertEqual(self.line_values(payout), [(order_id, "upi", 3.3, 1001, 0, 33, 968)])
		self.assertEqual((payout.total_commission, payout.total_net), (33, 968))

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

	def test_settled_payment_is_not_pulled_again(self):
		self.paid_order(1000)
		self.submit(self.payout_with_payments())
		self.assertEqual(self.payout_with_payments().lines, [])

	def test_payment_on_two_draft_payouts_settles_once(self):
		order_id = self.paid_order(1000)
		first, second = self.payout_with_payments(), self.payout_with_payments()
		self.submit(first)
		with self.assertRaises(frappe.ValidationError):
			self.submit(second, transfer_reference="UTR-1002")
		self.assertEqual(self.payout_of(order_id), first.name)

	def test_unpaid_payment_is_not_pulled(self):
		with self.set_user(self.integration):
			create_order(**self.order_values(amount=1000))
		self.assertEqual(self.payout_with_payments().lines, [])

	def test_payment_outside_the_dates_is_not_pulled(self):
		self.paid_order(1000)
		payout = self.payout_with_payments(from_date=add_days(today(), 1), to_date=add_days(today(), 7))
		self.assertEqual(payout.lines, [])

	def test_payment_is_pulled_by_the_day_it_was_paid(self):
		with self.freeze_time(add_days(now_datetime(), -3)):
			with self.set_user(self.integration):
				order_id = create_order(**self.order_values(amount=1000)).order_id
		payment_testing.pay(frappe.db.get_value("Hosted Payment", order_id, "payment_request"))
		ordered_day = add_days(today(), -3)
		self.assertEqual(self.payout_with_payments(from_date=ordered_day, to_date=ordered_day).lines, [])
		self.assertEqual([line.hosted_payment for line in self.payout_with_payments().lines], [order_id])

	def test_payment_of_another_team_cannot_be_submitted(self):
		self.paid_order(1000)
		payout = self.payout_with_payments()
		payout.team = BuzzTeamFactory.create_owned_by().name
		payout.save()
		with self.assertRaises(frappe.ValidationError):
			self.submit(payout)

	def test_payment_in_another_currency_cannot_be_submitted(self):
		self.paid_order(1000)
		payout = self.payout_with_payments()
		payout.currency = "USD"
		payout.save()
		with self.assertRaises(frappe.ValidationError):
			self.submit(payout)

	def test_refund_after_settlement_is_a_negative_line_on_the_next_payout(self):
		order_id = self.paid_order(1000)
		first = self.submit(self.payout_with_payments())
		self.refund(order_id, 300)
		payout = self.payout_with_payments()
		self.assertEqual(self.line_values(payout), [(order_id, "upi", 0, 0, 300, 0, -300)])
		self.assertEqual(payout.total_net, -300)
		self.submit(payout, transfer_reference="UTR-1002")
		self.assertEqual(self.payout_of(order_id), first.name)

	def test_refund_is_carried_forward_once(self):
		order_id = self.paid_order(1000)
		self.refund(order_id, 100)
		self.submit(self.payout_with_payments())
		self.refund(order_id, 300)
		self.submit(self.payout_with_payments(), transfer_reference="UTR-1002")
		self.refund(order_id, 200)
		payout = self.payout_with_payments()
		self.assertEqual(self.line_values(payout), [(order_id, "upi", 0, 0, 200, 0, -200)])

	def test_carried_forward_refund_on_two_draft_payouts_is_deducted_once(self):
		order_id = self.paid_order(1000)
		self.submit(self.payout_with_payments())
		self.refund(order_id, 300)
		first, second = self.payout_with_payments(), self.payout_with_payments()
		self.submit(first, transfer_reference="UTR-1002")
		with self.assertRaises(frappe.ValidationError):
			self.submit(second, transfer_reference="UTR-1003")

	def test_payout_without_lines_cannot_be_submitted(self):
		with self.assertRaises(frappe.ValidationError):
			self.submit(self.payout_with_payments())

	def test_cancel_releases_the_payments(self):
		order_id = self.paid_order(1000)
		self.submit(self.payout_with_payments()).cancel()
		self.assertIsNone(self.payout_of(order_id))
		payout = self.payout_with_payments()
		self.assertEqual(self.line_values(payout), [(order_id, "upi", 3.3, 1000, 0, 33, 967)])

	def test_cancel_releases_a_carried_forward_refund(self):
		order_id = self.paid_order(1000)
		self.submit(self.payout_with_payments())
		self.refund(order_id, 300)
		self.submit(self.payout_with_payments(), transfer_reference="UTR-1002").cancel()
		payout = self.payout_with_payments()
		self.assertEqual(self.line_values(payout), [(order_id, "upi", 0, 0, 300, 0, -300)])

	def test_payout_whose_refunds_a_later_payout_deducted_cannot_be_cancelled(self):
		order_id = self.paid_order(1000)
		first = self.submit(self.payout_with_payments())
		self.refund(order_id, 300)
		self.submit(self.payout_with_payments(), transfer_reference="UTR-1002")
		with self.assertRaises(frappe.ValidationError):
			first.cancel()
		self.assertEqual(self.payout_of(order_id), first.name)

	def test_unpaid_payment_cannot_be_submitted(self):
		order_id = HostedPaymentFactory.create(
			team=self.team, paid_on=now_datetime(), payment_method="upi"
		).name
		line = {"hosted_payment": order_id, "line_type": "Payment", "payment_method": "upi", "rate": 3.3}
		line |= {"gross": 1000, "refunded": 0, "commission": 33, "net": 967}
		payout = HostedPayoutFactory.create(team=self.team, lines=[line])
		with self.assertRaisesRegex(frappe.ValidationError, "Get payments again"):
			self.submit(payout)
		self.assertIsNone(self.payout_of(order_id))

	def submit_with_line_changed(self, payout, **values) -> None:
		payout.lines[0].update(values)
		payout.save()
		with self.assertRaisesRegex(frappe.ValidationError, "Get payments again"):
			self.submit(payout, transfer_reference="UTR-1002")

	def test_refund_line_that_adds_to_the_transfer_is_rejected(self):
		order_id = self.paid_order(1000)
		self.submit(self.payout_with_payments())
		self.refund(order_id, 300)
		self.submit_with_line_changed(self.payout_with_payments(), net=300)
		self.assertEqual(
			self.line_values(self.payout_with_payments()), [(order_id, "upi", 0, 0, 300, 0, -300)]
		)

	def test_refund_line_with_gross_or_commission_is_rejected(self):
		order_id = self.paid_order(1000)
		self.submit(self.payout_with_payments())
		self.refund(order_id, 300)
		for values in ({"gross": 300}, {"commission": 10, "net": -310}):
			with self.subTest(values=values):
				self.submit_with_line_changed(self.payout_with_payments(), **values)

	def test_payment_line_with_values_other_than_the_payment_is_rejected(self):
		self.paid_order(1000)
		for values in ({"gross": 2000, "net": 1967}, {"commission": 0, "net": 1000}, {"rate": 0}):
			with self.subTest(values=values):
				self.submit_with_line_changed(self.payout_with_payments(), **values)

	def test_rate_changed_after_get_payments_submits_at_the_frozen_rate(self):
		order_id = self.paid_order(1000)
		payout = self.payout_with_payments()
		self.set_rates({"upi": 5}, fallback_rate=5)
		self.submit(payout)
		self.assertEqual(self.line_values(payout), [(order_id, "upi", 3.3, 1000, 0, 33, 967)])
		self.assertEqual(self.payout_of(order_id), payout.name)

	def test_get_payments_again_takes_the_new_rate(self):
		order_id = self.paid_order(1000)
		payout = self.payout_with_payments()
		self.set_rates({"upi": 5}, fallback_rate=5)
		payout.get_payments()
		self.submit(payout)
		self.assertEqual(self.line_values(payout), [(order_id, "upi", 5, 1000, 0, 50, 950)])

	def test_rates_sent_with_the_payout_are_not_trusted(self):
		self.paid_order(1000)
		payout = self.payout_with_payments()
		payout.commission_rates = {"rates": {"upi": 0}, "fallback_rate": 0}
		self.submit_with_line_changed(payout, rate=0, commission=0, net=1000)

	def test_payment_refunded_after_the_payout_was_drawn_up_is_rejected(self):
		order_id = self.paid_order(1000)
		payout = self.payout_with_payments()
		self.refund(order_id, 400)
		with self.assertRaisesRegex(frappe.ValidationError, "Get payments again"):
			self.submit(payout)
		self.assertIsNone(self.payout_of(order_id))

	def repeat_first_line(self, payout) -> None:
		fields = ("hosted_payment", "line_type", "payment_method", "rate", "gross", "refunded", "commission")
		payout.append("lines", {field: payout.lines[0].get(field) for field in (*fields, "net")})

	def test_payment_twice_in_one_payout_is_rejected(self):
		self.paid_order(1000)
		payout = self.payout_with_payments()
		self.repeat_first_line(payout)
		with self.assertRaises(frappe.ValidationError):
			payout.save()

	def test_refund_twice_in_one_payout_is_rejected(self):
		order_id = self.paid_order(1000)
		self.submit(self.payout_with_payments())
		self.refund(order_id, 300)
		payout = self.payout_with_payments()
		self.repeat_first_line(payout)
		with self.assertRaises(frappe.ValidationError):
			payout.save()
