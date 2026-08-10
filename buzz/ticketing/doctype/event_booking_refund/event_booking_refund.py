# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class EventBookingRefund(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		cancellation_request: DF.Link | None
		currency: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		refund_id: DF.Data | None
		status: DF.Literal["Initiated", "Processed", "Failed"]
		tickets: DF.SmallText | None
	# end: auto-generated types

	pass
