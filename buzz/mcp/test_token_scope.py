from frappe.permissions import ALL_USER_ROLE, SYSTEM_USER_ROLE
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import OAuthClientFactory
from buzz.tests.mcp_test_case import ENDPOINT, McpTestCase

LOGGED_USER = "/api/method/frappe.auth.get_logged_user"


class TestTokenScope(McpTestCase):
	def setUp(self):
		super().setUp()
		self.user = self.website_user("mcp-attendee@example.com")
		self.mcp_token = self.bearer_for(self.user)

	def get(self, path: str, authorization: str):
		return self.post(method="GET", body="", path=path, authorization=authorization)

	def test_mcp_token_reaches_the_mcp_endpoint(self):
		self.assertEqual(self.rpc("ping", authorization=self.mcp_token).status_code, 200)

	def test_mcp_token_reaches_userinfo(self):
		response = self.get("/api/method/frappe.integrations.oauth2.openid_profile", self.mcp_token)
		self.assertEqual(response.status_code, 200)

	def test_mcp_token_is_refused_elsewhere(self):
		for path in (LOGGED_USER, "/api/v2/method/frappe.auth.get_logged_user", "/api/v2/document/User"):
			with self.subTest(path=path):
				self.assertEqual(self.get(path, self.mcp_token).status_code, 403)

	def test_cmd_cannot_ride_on_the_mcp_path(self):
		response = self.get(f"{ENDPOINT}?cmd=frappe.auth.get_logged_user", self.mcp_token)
		self.assertEqual(response.status_code, 403)

	def test_tokens_of_registered_apps_are_not_confined(self):
		client = OAuthClientFactory.create().name
		authorization = self.bearer_for(self.user, client=client)
		self.assertEqual(self.get(LOGGED_USER, authorization).status_code, 200)


class TestDynamicClientRoles(IntegrationTestCase):
	def roles(self, client) -> list[str]:
		return [row.role for row in client.allowed_roles]

	def test_any_signed_in_user_can_authorize_an_mcp_client(self):
		self.assertEqual(self.roles(OAuthClientFactory.create("dynamic")), [ALL_USER_ROLE])

	def test_registered_apps_keep_frappe_default(self):
		self.assertEqual(self.roles(OAuthClientFactory.create()), [SYSTEM_USER_ROLE])
