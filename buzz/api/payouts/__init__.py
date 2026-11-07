import frappe

from buzz.api.payouts.schemas import PayoutAccount
from buzz.api.payouts.services import PayoutAccountService


@frappe.whitelist()
def get_payout_account(team: str) -> PayoutAccount:
	return PayoutAccountService(team).details()


@frappe.whitelist(methods=["POST"])
def submit_payout_account(team: str, details: dict) -> PayoutAccount:
	"""Create the team's payout account, or resend its details when the gateway asked for changes."""
	return PayoutAccountService(team).submit(details)


@frappe.whitelist(methods=["POST"])
def refresh_payout_account(team: str) -> PayoutAccount:
	return PayoutAccountService(team).refresh()
