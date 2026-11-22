from buzz.api.schemas import APIResponse


class HostedOrder(APIResponse):
	order_id: str
	checkout_url: str
