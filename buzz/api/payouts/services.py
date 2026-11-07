import frappe
from bwh_payments import api as payments
from frappe import _
from pydantic import ValidationError

from buzz.api.payouts.exceptions import (
	InvalidPayoutDetails,
	NotTeamOwner,
	PayoutsNotConfigured,
	PayoutsNotEnabled,
)
from buzz.api.payouts.schemas import PayoutAccount
from buzz.events.doctype.buzz_team_settings.buzz_team_settings import is_feature_enabled
from buzz.permissions import team_role_of

PAYOUTS_FLAG = "feature_payouts"


class PayoutAccountService:
	"""A team's payout account on the site's payout gateway.

	Owners only: the account decides where the team's money goes.
	"""

	def __init__(self, team: str):
		if team_role_of(frappe.session.user, team) != "Owner":
			NotTeamOwner.throw()
		if not is_feature_enabled(team, PAYOUTS_FLAG):
			PayoutsNotEnabled.throw()
		self.team = team
		self.gateway = frappe.db.get_single_value("Buzz Settings", "payout_gateway")
		if not self.gateway:
			PayoutsNotConfigured.throw()

	def details(self) -> PayoutAccount:
		account = self.get_account()
		if not account:
			return PayoutAccount(status=None, requirements=[])
		return PayoutAccount(
			status=account.status, requirements=frappe.parse_json(account.requirements) or []
		)

	def submit(self, details: dict) -> PayoutAccount:
		try:
			payments.submit_linked_account(self.gateway, "Buzz Team", self.team, details)
		except ValidationError as error:
			first = error.errors()[0]
			InvalidPayoutDetails.throw(
				field=".".join(str(part) for part in first["loc"]), reason=first["msg"]
			)
		notify_owners(self.team)
		return self.details()

	def refresh(self) -> PayoutAccount:
		if account := self.get_account():
			payments.sync_linked_account(account.name)
		return self.details()

	def get_account(self):
		return frappe.db.get_value(
			"Gateway Linked Account",
			{
				"gateway": self.gateway,
				"ref_doctype": "Buzz Team",
				"ref_docname": self.team,
				"status": ("!=", "Suspended"),
			},
			["name", "status", "requirements"],
			as_dict=True,
		)


def notify_owners(team: str):
	"""Changing where payouts go is the one change an account takeover would want hidden."""
	owners = frappe.get_all(
		"Buzz Team Membership", filters={"team": team, "team_role": "Owner", "enabled": 1}, pluck="user"
	)
	team_name = frappe.db.get_value("Buzz Team", team, "team_name")
	frappe.sendmail(
		recipients=owners,
		subject=_("Payout details changed for {0}").format(team_name),
		message=_(
			"{0} just submitted new payout details for {1}. If this was not someone on your team,"
			" contact support at once."
		).format(frappe.session.user, team_name),
	)
