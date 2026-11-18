from frappe import _lt

from buzz.api.exceptions import BuzzAPIError


class QuotaExceeded(BuzzAPIError):
	http_status_code = 429
	title = _lt("Usage Limit Reached")
	message = _lt(
		"You have reached the {window} limit for AI assistant tool calls. It resets at {resets_at} UTC."
	)
