import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.payments import get_event_payment_gateways


class TestGetEventPaymentGateways(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = str(frappe.get_doc("Buzz Event", {"route": "test-route"}).name)

	def setUp(self):
		frappe.set_user("Administrator")
		gateway = {"doctype": "Payment Gateway", "gateway": f"Test Gateway {frappe.generate_hash(6)}"}
		self.gateway = frappe.get_doc(gateway).insert().name
		self.set_gateways([])
		self.set_default(None)

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

	def set_default(self, gateway: str | None):
		frappe.db.set_single_value("Buzz Settings", "default_payment_gateway", gateway)
		self.addCleanup(frappe.clear_document_cache, "Buzz Settings", "Buzz Settings")

	def test_configured_gateways_override_default(self):
		other = frappe.get_doc({"doctype": "Payment Gateway", "gateway": f"Other {frappe.generate_hash(6)}"})
		self.set_default(other.insert().name)
		self.set_gateways([self.gateway])

		self.assertEqual(get_event_payment_gateways(self.event), [self.gateway])

	def test_no_gateways_configured(self):
		self.assertEqual(get_event_payment_gateways(self.event), [])

	def test_falls_back_to_default_gateway(self):
		self.set_default(self.gateway)

		self.assertEqual(get_event_payment_gateways(self.event), [self.gateway])
