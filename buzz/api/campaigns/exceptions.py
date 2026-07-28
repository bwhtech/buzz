from frappe import _lt

from buzz.api.exceptions import BuzzAPIError, Conflict


class CampaignNotActive(Conflict):
	title = _lt("Campaign Closed")
	message = _lt("This campaign is no longer accepting registrations.")


class AlreadyRegistered(Conflict):
	title = _lt("Already Registered")
	message = _lt("You have already registered your interest in this campaign.")


class CRMNotAvailable(BuzzAPIError):
	# Deliberately 4xx: the CRM app being absent is a site configuration gap, and a 5xx would
	# write an Error Log on every click.
	title = _lt("Unavailable")
	message = _lt("Campaign registration is not available right now.")
