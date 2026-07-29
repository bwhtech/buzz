from frappe import _lt

from buzz.api.exceptions import Conflict, NotPermitted


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
