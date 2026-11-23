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
		# Frappe 16 has no is_dynamic_client; there a Guest owner marks a registered client.
		return {"is_dynamic_client": 1, "owner": "Guest", "token_endpoint_auth_method": "None"}

	@classmethod
	def create(cls, *factory_traits: str, **overrides: Any) -> OAuthClient:
		client = super().create(*factory_traits, **overrides)
		# Frappe 16 replaces owner with the session user on insert; registration runs as Guest.
		if "dynamic" in factory_traits and client.owner != "Guest":
			client.db_set("owner", "Guest", update_modified=False)
		return client
