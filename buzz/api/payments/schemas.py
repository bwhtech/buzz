from buzz.api.schemas import APIResponse


class CurrencyItem(APIResponse):
	name: str
	symbol: str | None
	number_format: str | None
