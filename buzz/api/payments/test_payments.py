import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.payments import get_event_payment_gateways


class TestGetEventPaymentGateways(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = str(frappe.get_doc("Buzz Event", {"route": "test-route"}).name)
		cls.gateway = frappe.get_all("Payment Gateway", pluck="name", limit=1)[0]

	def setUp(self):
		frappe.set_user("Administrator")
		self.set_gateways([])

	def tearDown(self):
		frappe.db.rollback()
		frappe.clear_document_cache("Buzz Event", self.event)

	def set_gateways(self, gateways: list[str]):
		event = frappe.get_doc("Buzz Event", self.event)
		event.payment_gateways = []
		for gateway in gateways:
			event.append("payment_gateways", {"payment_gateway": gateway})
		event.save(ignore_permissions=True)
		frappe.clear_document_cache("Buzz Event", self.event)

	def test_configured_gateways_are_returned(self):
		self.set_gateways([self.gateway])

		self.assertEqual(get_event_payment_gateways(self.event), [self.gateway])

	def test_no_gateways_configured(self):
		self.assertEqual(get_event_payment_gateways(self.event), [])
