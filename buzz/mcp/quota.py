import time
from datetime import UTC, datetime

import frappe

from buzz.mcp.exceptions import QuotaExceeded

WINDOWS = (("hourly", 3600, "mcp_calls_per_hour"), ("daily", 86400, "mcp_calls_per_day"))


class UsageQuota:
	"""Counts one user's MCP tool calls in fixed clock windows: the hour and the UTC day."""

	def __init__(self, user: str):
		self.user = user

	def consume(self) -> None:
		for window, seconds, setting in WINDOWS:
			limit = frappe.db.get_single_value("Buzz Settings", setting)
			if limit and self.count(window, seconds) >= limit:
				QuotaExceeded.throw(window=window, resets_at=self.resets_at(seconds))
		for window, seconds, _setting in WINDOWS:
			self.increment(window, seconds)

	def key(self, window: str, seconds: int) -> str:
		bucket = int(time.time()) // seconds
		return frappe.cache.make_key(f"buzz:mcp:{window}:{bucket}:{self.user}")

	def count(self, window: str, seconds: int) -> int:
		# The key is site-scoped by make_key; the counter is a raw Redis integer, not a pickled value.
		value = frappe.cache.get(self.key(window, seconds))  # nosemgrep: frappe-cache-breaks-multitenancy
		return int(value or 0)

	def increment(self, window: str, seconds: int) -> None:
		key = self.key(window, seconds)
		frappe.cache.set(key, 0, ex=seconds, nx=True)  # nosemgrep: frappe-cache-breaks-multitenancy
		frappe.cache.incrby(key, 1)

	@staticmethod
	def resets_at(seconds: int) -> str:
		next_window = (int(time.time()) // seconds + 1) * seconds
		return datetime.fromtimestamp(next_window, UTC).strftime("%Y-%m-%d %H:%M")
