from bwh_payments import api as payments


def round_to_currency(amount: float, currency: str) -> float:
	"""Rounded to the currency's minor unit, such as 3 decimals for KWD and none for JPY, as bwh_payments
	rounds it."""
	return payments.from_minor_units(payments.to_minor_units(amount, currency), currency)
