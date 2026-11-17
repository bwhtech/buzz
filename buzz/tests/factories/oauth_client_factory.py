from typing import Any

from frappe.integrations.doctype.oauth_client.oauth_client import OAuthClient
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory


class OAuthClientFactory(BaseFactory[OAuthClient]):
	doctype = "OAuth Client"

	@property
	def default_attributes(self) -> dict[str, Any]:
		return {
			"app_name": "Test MCP Client",
			"default_redirect_uri": "http://localhost:33418/callback",
			"redirect_uris": "http://localhost:33418/callback",
		}

	@property
	def dynamic(self) -> dict[str, Any]:
		return {"is_dynamic_client": 1, "token_endpoint_auth_method": "None"}
