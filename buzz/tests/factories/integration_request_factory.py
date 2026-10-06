from typing import Any

from frappe.integrations.doctype.integration_request.integration_request import IntegrationRequest
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory


class IntegrationRequestFactory(BaseFactory[IntegrationRequest]):
	"""A queued Razorpay webhook. Pass the payload as JSON in `data`."""

	doctype = "Integration Request"

	@property
	def default_attributes(self) -> dict[str, Any]:
		return {"integration_request_service": "Razorpay", "is_remote_request": 1, "status": "Queued"}
