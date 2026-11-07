from frappe import _lt

from buzz.api.exceptions import BuzzAPIError, NotPermitted


class NotTeamOwner(NotPermitted):
	message = _lt("Only the team's owner can manage where its payouts go.")


class PayoutsNotEnabled(NotPermitted):
	message = _lt("Payouts are not enabled for this team. Contact your administrator.")


class PayoutsNotConfigured(BuzzAPIError):
	message = _lt("Payouts are not set up on this site yet.")


class InvalidPayoutDetails(BuzzAPIError):
	title = _lt("Check the Details")
	message = _lt("{field}: {reason}")
