import json

import frappe
from frappe.tests import IntegrationTestCase
from frappe.tests.test_api import make_request
from frappe.utils import get_test_client

from buzz.tests.factories import OAuthBearerTokenFactory, UserFactory

ENDPOINT = "/api/v2/method/buzz.mcp.endpoint.handle"


class McpTestCase(IntegrationTestCase):
	"""Sends MCP requests over HTTP with an OAuth bearer token, as a real MCP client does.

	The test client runs on another database connection, so fixtures are committed and
	removed in cleanup.
	"""

	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.clear_document_cache, "Buzz Settings", "Buzz Settings")
		self.set_buzz_settings(
			enable_mcp=1, mcp_requests_per_minute=0, mcp_calls_per_hour=0, mcp_calls_per_day=0
		)

	def set_buzz_settings(self, **values):
		original = {field: frappe.db.get_single_value("Buzz Settings", field) for field in values}
		frappe.db.set_single_value("Buzz Settings", values)
		self.addCleanup(self.restore_buzz_settings, original)

	def restore_buzz_settings(self, values: dict):
		frappe.db.set_single_value("Buzz Settings", values)
		frappe.db.commit()  # nosemgrep: frappe-manual-commit -- settings are read by the test client's connection
		frappe.clear_document_cache("Buzz Settings", "Buzz Settings")

	def bearer_for(self, user: str, **token_overrides) -> str:
		access_token = frappe.generate_hash()
		token = OAuthBearerTokenFactory.create(user=user, access_token=access_token, **token_overrides)
		self.addCleanup(self.delete_committed, "OAuth Bearer Token", token.name)
		self.addCleanup(self.delete_committed, "OAuth Client", token.client)
		return f"Bearer {access_token}"

	def website_user(self, email: str) -> str:
		return UserFactory.create_once(email).name

	def fresh_user(self) -> str:
		"""Rate and quota counters are per user, so a test that counts needs a user of its own."""
		user = UserFactory.create(flags={"ignore_permissions": True}).name
		self.addCleanup(self.delete_committed, "User", user)
		return user

	def delete_committed(self, doctype: str, name: str):
		frappe.delete_doc_if_exists(doctype, name, force=True)
		frappe.db.commit()  # nosemgrep: frappe-manual-commit -- fixture cleanup for the test client's connection

	def post(
		self, payload=None, *, authorization=None, headers=None, method="POST", path=ENDPOINT, body=None
	):
		request_headers = {"Content-Type": "application/json", "Accept": "application/json"}
		if authorization:
			request_headers["Authorization"] = authorization
		request_headers.update(headers or {})
		frappe.db.commit()  # nosemgrep: frappe-manual-commit -- the test client reads committed fixtures
		try:
			return make_request(
				get_test_client(use_cookies=False).open,
				args=(),
				kwargs={
					"path": path,
					"method": method,
					"headers": request_headers,
					"data": body if body is not None else json.dumps(payload),
				},
				site=frappe.local.site,
			)
		finally:
			frappe.db.rollback()

	def rpc(self, method: str, params: dict | None = None, **kwargs):
		payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
		return self.post(payload, **kwargs)

	def call_tool(self, name: str, arguments: dict | None = None, **kwargs) -> dict:
		response = self.rpc("tools/call", {"name": name, "arguments": arguments or {}}, **kwargs)
		return response.json["result"]
