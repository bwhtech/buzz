from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.payments import (
	get_event_payment_gateways,
	get_payment_gateway_logos,
	get_payment_gateways_needing_phone,
)
from buzz.payments import resolve_payment_gateway
from buzz.tests.base_test_cases import make_payment_gateway
from buzz.tests.factories import BuzzEventFactory


class TestGetEventPaymentGateways(IntegrationTestCase):
	def setUp(self):
		self.enterContext(self.change_settings("Buzz Settings", default_payment_gateway=None))
		self.gateway = make_payment_gateway()
		self.other_gateway = make_payment_gateway()

	def test_configured_gateways_override_default(self):
		event = self.create_event(self.gateway)

		with self.change_settings("Buzz Settings", default_payment_gateway=self.other_gateway):
			self.assertEqual(get_event_payment_gateways(event), [self.gateway])

	def test_no_gateways_configured(self):
		self.assertEqual(get_event_payment_gateways(self.create_event()), [])

	def test_falls_back_to_default_gateway(self):
		event = self.create_event()

		with self.change_settings("Buzz Settings", default_payment_gateway=self.gateway):
			self.assertEqual(get_event_payment_gateways(event), [self.gateway])

	def test_new_event_starts_with_default_gateway(self):
		with self.change_settings("Buzz Settings", default_payment_gateway=self.gateway):
			event = self.create_event()

		self.assertEqual(self.gateways_on(event), [self.gateway])

	def test_new_event_keeps_gateways_it_was_created_with(self):
		with self.change_settings("Buzz Settings", default_payment_gateway=self.gateway):
			event = self.create_event(self.other_gateway)

		self.assertEqual(self.gateways_on(event), [self.other_gateway])

	def test_a_disabled_gateway_is_not_offered(self):
		event = self.create_event(self.gateway, self.other_gateway)
		frappe.get_doc("Payment Gateway Profile", self.other_gateway).update({"enabled": 0}).save()

		self.assertEqual(get_event_payment_gateways(event), [self.gateway])

	def test_resolve_picks_the_first_gateway_when_none_is_given(self):
		self.assertEqual(resolve_payment_gateway(self.create_event(self.gateway), None), self.gateway)

	def test_resolve_accepts_a_gateway_the_event_uses(self):
		event = self.create_event(self.gateway)

		self.assertEqual(resolve_payment_gateway(event, self.gateway), self.gateway)

	def test_resolve_rejects_a_gateway_the_event_does_not_use(self):
		event = self.create_event(self.gateway)

		with self.assertRaises(frappe.ValidationError):
			resolve_payment_gateway(event, self.other_gateway)

	def test_resolve_throws_when_the_event_has_no_gateway(self):
		with self.assertRaises(frappe.ValidationError):
			resolve_payment_gateway(self.create_event(), None)

	def create_event(self, *gateways: str) -> str:
		rows = [{"payment_gateway": gateway} for gateway in gateways]
		return str(BuzzEventFactory.create(payment_gateways=rows).name)

	def gateways_on(self, event: str) -> list[str]:
		return [row.payment_gateway for row in frappe.get_doc("Buzz Event", event).payment_gateways]


class TestGetPaymentGatewaysNeedingPhone(IntegrationTestCase):
	def test_lists_enabled_gateways_whose_checkout_needs_a_phone(self):
		gateway = make_payment_gateway()

		with patch("buzz.payments.GATEWAYS_NEEDING_PHONE", ("Razorpay Gateway Settings",)):
			self.assertIn(gateway, get_payment_gateways_needing_phone())

	def test_leaves_out_gateways_that_do_not_need_one(self):
		gateway = make_payment_gateway()

		with patch("buzz.payments.GATEWAYS_NEEDING_PHONE", ("PayU Gateway Settings",)):
			self.assertNotIn(gateway, get_payment_gateways_needing_phone())

	def test_leaves_out_a_disabled_gateway(self):
		gateway = make_payment_gateway()
		frappe.db.set_value("Payment Gateway Profile", gateway, "enabled", 0)

		with patch("buzz.payments.GATEWAYS_NEEDING_PHONE", ("Razorpay Gateway Settings",)):
			self.assertNotIn(gateway, get_payment_gateways_needing_phone())


class TestGetPaymentGatewayLogos(IntegrationTestCase):
	def test_every_enabled_gateway_comes_with_its_logo_for_both_themes(self):
		gateway = make_payment_gateway()

		logos = {row.name: row for row in get_payment_gateway_logos()}

		self.assertTrue(logos[gateway].logo.startswith("/assets/bwh_payments/"))
		self.assertTrue(logos[gateway].logo_dark.startswith("/assets/bwh_payments/"))

	def test_a_disabled_gateway_has_no_logo_listed(self):
		gateway = make_payment_gateway()
		frappe.get_doc("Payment Gateway Profile", gateway).update({"enabled": 0}).save()

		self.assertNotIn(gateway, [row.name for row in get_payment_gateway_logos()])
