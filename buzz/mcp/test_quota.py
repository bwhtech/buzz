import frappe
from frappe.tests import IntegrationTestCase

from buzz.mcp.exceptions import QuotaExceeded
from buzz.mcp.quota import UsageQuota


class TestUsageQuota(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self.user = f"quota-{frappe.generate_hash(length=8)}@example.com"
		self.addCleanup(frappe.clear_document_cache, "Buzz Settings", "Buzz Settings")

	def limits(self, hour: int, day: int):
		return self.change_settings("Buzz Settings", mcp_calls_per_hour=hour, mcp_calls_per_day=day)

	def test_calls_within_the_limit_pass(self):
		with self.limits(hour=2, day=10):
			UsageQuota(self.user).consume()
			UsageQuota(self.user).consume()

	def test_hourly_limit_names_the_reset_time(self):
		with self.limits(hour=1, day=10):
			UsageQuota(self.user).consume()
			with self.assertRaisesRegex(QuotaExceeded, "hourly.*UTC"):
				UsageQuota(self.user).consume()

	def test_daily_limit(self):
		with self.limits(hour=10, day=1):
			UsageQuota(self.user).consume()
			with self.assertRaisesRegex(QuotaExceeded, "daily"):
				UsageQuota(self.user).consume()

	def test_each_user_has_their_own_count(self):
		with self.limits(hour=1, day=10):
			UsageQuota(self.user).consume()
			UsageQuota(f"other-{self.user}").consume()

	def test_zero_means_no_limit(self):
		with self.limits(hour=0, day=0):
			for _ in range(3):
				UsageQuota(self.user).consume()

	def test_a_refused_call_is_not_counted(self):
		with self.limits(hour=10, day=1):
			UsageQuota(self.user).consume()
			with self.assertRaises(QuotaExceeded):
				UsageQuota(self.user).consume()
		with self.limits(hour=2, day=10):
			UsageQuota(self.user).consume()
