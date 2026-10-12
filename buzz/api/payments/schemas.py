from buzz.api.schemas import APIResponse


class CurrencyItem(APIResponse):
	name: str
	symbol: str | None
	number_format: str | None


class PaymentGatewayLogo(APIResponse):
	name: str
	logo: str
	logo_dark: str
