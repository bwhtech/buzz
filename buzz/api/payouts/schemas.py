from buzz.api.schemas import APIResponse


class PayoutAccount(APIResponse):
	"""Where a team's payout account stands. The business and bank details are never stored, so never returned."""

	# None until the owner submits the account.
	status: str | None
	# What the gateway still needs before it activates the account.
	requirements: list[dict]
