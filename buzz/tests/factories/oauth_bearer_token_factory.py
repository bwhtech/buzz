from typing import Any

import frappe
from frappe.integrations.doctype.oauth_bearer_token.oauth_bearer_token import OAuthBearerToken
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory


class OAuthBearerTokenFactory(BaseFactory[OAuthBearerToken]):
	"""`access_token` is hashed on insert, so pass the raw token in to send it later."""

	doctype = "OAuth Bearer Token"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories.oauth_client_factory import OAuthClientFactory

		return {
			"client": self.overrides.get("client") or OAuthClientFactory.create("dynamic").name,
			"access_token": frappe.generate_hash(),
			"expires_in": 3600,
			"scopes": "all openid",
			"status": "Active",
		}
