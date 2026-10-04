from frappe import _lt

from buzz.api.exceptions import Conflict, NotPermitted, ResourceNotFound


class EnquiryNotFound(ResourceNotFound):
	message = _lt("This sponsorship enquiry does not exist.")


class EnquiryNotAccessible(NotPermitted):
	message = _lt("You are not permitted to view this sponsorship enquiry.")


class PaymentNotPermitted(NotPermitted):
	message = _lt("You are not permitted to pay for this sponsorship enquiry.")


class WithdrawalNotPermitted(NotPermitted):
	message = _lt("You are not permitted to withdraw this sponsorship enquiry.")


class EnquiryAlreadyPaid(Conflict):
	title = _lt("Already Paid")
	message = _lt("A paid sponsorship enquiry cannot be withdrawn.")


class EnquiryAlreadyWithdrawn(Conflict):
	title = _lt("Already Withdrawn")
	message = _lt("This sponsorship enquiry has already been withdrawn.")


class EnquiryStatusLocked(Conflict):
	title = _lt("Status Locked")
	message = _lt("A paid, cancelled or withdrawn sponsorship enquiry keeps its status.")


class EnquiryTierMissing(Conflict):
	title = _lt("No Tier")
	message = _lt("Pick a sponsorship tier for this enquiry first.")
