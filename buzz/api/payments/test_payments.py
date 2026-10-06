import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.payments import get_event_payment_gateways
from buzz.payments import resolve_payment_gateway
from buzz.tests.factories import BuzzEventFactory, PaymentGatewayFactory


class TestGetEventPaymentGateways(IntegrationTestCase):
	def setUp(self):
		self.enterContext(self.change_settings("Buzz Settings", default_payment_gateway=None))
		self.gateway = PaymentGatewayFactory.create().name
		self.other_gateway = PaymentGatewayFactory.create().name

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
