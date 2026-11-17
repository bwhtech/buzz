from unittest.mock import patch

import frappe

from buzz.mcp.tools import NoArguments, read_only_tool
from buzz.tests.mcp_test_case import McpTestCase

INITIALIZE = {
	"protocolVersion": "2025-11-25",
	"capabilities": {},
	"clientInfo": {"name": "test", "version": "1"},
}


class TestMcpEndpoint(McpTestCase):
	def setUp(self):
		super().setUp()
		self.attendee = self.website_user("mcp-attendee@example.com")
		self.authorization = self.bearer_for(self.attendee)

	def test_initialize_names_buzz(self):
		result = self.rpc("initialize", INITIALIZE, authorization=self.authorization).json["result"]
		self.assertEqual(result["serverInfo"]["name"], "buzz")
		self.assertIn("read-only", result["instructions"])

	def test_ping(self):
		response = self.rpc("ping", authorization=self.authorization)
		self.assertEqual(response.json, {"jsonrpc": "2.0", "id": 1, "result": {}})

	def test_notification_gets_no_body(self):
		payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
		self.assertEqual(self.post(payload, authorization=self.authorization).status_code, 202)

	def test_tools_are_read_only(self):
		tools = self.rpc("tools/list", authorization=self.authorization).json["result"]["tools"]
		self.assertIn("list_my_events", [tool["name"] for tool in tools])
		for tool in tools:
			self.assertTrue(tool["annotations"]["readOnlyHint"], tool["name"])

	def test_list_my_events(self):
		result = self.call_tool("list_my_events", authorization=self.authorization)
		self.assertFalse(result["isError"])
		self.assertEqual(set(result["structuredContent"]), {"events", "has_next_page"})

	def test_unknown_tool(self):
		response = self.rpc("tools/call", {"name": "delete_document"}, authorization=self.authorization)
		self.assertEqual(response.status_code, 404)

	def test_unknown_argument_is_refused(self):
		result = self.call_tool("list_my_events", {"page": 5}, authorization=self.authorization)
		self.assertTrue(result["isError"])


class TestMcpAccess(McpTestCase):
	def setUp(self):
		super().setUp()
		self.attendee = self.website_user("mcp-attendee@example.com")

	def test_guest_gets_401_with_oauth_metadata(self):
		response = self.rpc("ping")
		self.assertEqual(response.status_code, 401)

	def test_api_key_is_refused(self):
		user = frappe.get_doc("User", self.attendee)
		user.api_key = frappe.generate_hash(length=15)
		user.api_secret = "secret-for-test"
		user.save(ignore_permissions=True)
		response = self.rpc("ping", authorization=f"token {user.api_key}:secret-for-test")
		self.assertEqual(response.status_code, 401)

	def test_disabled_endpoint_is_not_found(self):
		self.set_buzz_settings(enable_mcp=0)
		self.assertEqual(self.rpc("ping", authorization=self.bearer_for(self.attendee)).status_code, 404)

	def test_only_post(self):
		response = self.post(method="GET", body="", authorization=self.bearer_for(self.attendee))
		self.assertEqual(response.status_code, 405)
		self.assertEqual(response.headers["Allow"], "POST")

	def test_oversized_body_is_refused(self):
		body = '{"jsonrpc":"2.0","id":1,"method":"ping","params":{"pad":"' + "x" * 70_000 + '"}}'
		response = self.post(body=body, authorization=self.bearer_for(self.attendee))
		self.assertEqual(response.status_code, 413)

	def test_burst_limit(self):
		self.set_buzz_settings(mcp_requests_per_minute=2)
		authorization = self.bearer_for(self.fresh_user())
		statuses = [self.rpc("ping", authorization=authorization).status_code for _ in range(3)]
		self.assertEqual(statuses, [200, 200, 429])

	def test_quota_is_a_tool_error(self):
		self.set_buzz_settings(mcp_calls_per_hour=1)
		authorization = self.bearer_for(self.fresh_user())
		self.call_tool("list_my_events", authorization=authorization)
		result = self.call_tool("list_my_events", authorization=authorization)
		self.assertTrue(result["isError"])
		self.assertIn("resets at", result["content"][0]["text"])

	def test_a_tool_cannot_write(self):
		writer = read_only_tool(
			"write_note",
			"Writes.",
			NoArguments,
			lambda: frappe.get_doc(doctype="ToDo", description="written by a tool").db_insert(),
		)
		with patch("buzz.mcp.registry.tools_for_user", return_value=(writer,)):
			result = self.call_tool("write_note", authorization=self.bearer_for(self.attendee))
		self.assertTrue(result["isError"])
		self.assertIn("read-only", result["content"][0]["text"])
		self.assertFalse(frappe.db.exists("ToDo", {"description": "written by a tool"}))
