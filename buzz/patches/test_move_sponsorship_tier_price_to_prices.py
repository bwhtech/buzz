import frappe
from frappe.tests import IntegrationTestCase

from buzz.patches.move_sponsorship_tier_price_to_prices import execute


class TestMoveSponsorshipTierPriceToPrices(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.has_column("Sponsorship Tier", "price"):
			self.skipTest("The legacy price column is gone from this site.")
		frappe.set_user("Administrator")
		self.tier = frappe.get_doc(
			{
				"doctype": "Sponsorship Tier",
				"event": frappe.db.get_value("Buzz Event", {"route": "test-route"}),
				"title": "Legacy price tier",
				"prices": [{"currency": "INR", "price": 1}],
			}
		).insert(ignore_permissions=True)
		frappe.db.delete("Buzz Price", {"parent": self.tier.name})
		tier = frappe.qb.DocType("Sponsorship Tier")
		frappe.qb.update(tier).set(tier.price, 750).set(tier.currency, "USD").where(
			tier.name == self.tier.name
		).run()

	def tearDown(self):
		frappe.db.rollback()

	def test_legacy_price_becomes_the_first_row(self):
		execute()
		execute()

		rows = frappe.get_all(
			"Buzz Price", filters={"parent": self.tier.name}, fields=["currency", "price", "idx"]
		)
		self.assertEqual([(row.currency, row.price, row.idx) for row in rows], [("USD", 750, 1)])
