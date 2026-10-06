import frappe
from frappe.tests import IntegrationTestCase

from buzz.patches.move_sponsorship_tier_price_to_prices import execute
from buzz.tests.factories import SponsorshipTierFactory


class TestMoveSponsorshipTierPriceToPrices(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.has_column("Sponsorship Tier", "price"):
			self.skipTest("The legacy price column is gone from this site.")
		self.enterContext(self.set_user("Administrator"))
		self.tier = SponsorshipTierFactory.create().name
		frappe.db.delete("Buzz Price", {"parent": self.tier})
		tier = frappe.qb.DocType("Sponsorship Tier")
		frappe.qb.update(tier).set(tier.price, 750).set(tier.currency, "USD").where(
			tier.name == self.tier
		).run()

	def test_legacy_price_becomes_the_first_row(self):
		execute()
		execute()

		rows = frappe.get_all(
			"Buzz Price", filters={"parent": self.tier}, fields=["currency", "price", "idx"]
		)
		self.assertEqual([(row.currency, row.price, row.idx) for row in rows], [("USD", 750, 1)])
