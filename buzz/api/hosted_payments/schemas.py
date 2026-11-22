from frappe.utils import validate_email_address, validate_phone_number
from pydantic import field_validator

from buzz.api.hosted_payments.exceptions import InvalidCustomer
from buzz.api.schemas import APIRequest, APIResponse


class OrderCustomer(APIRequest):
	email: str | None = None
	phone: str | None = None

	@field_validator("email")
	@classmethod
	def check_email(cls, email: str | None) -> str | None:
		if email and not validate_email_address(email):
			InvalidCustomer.throw(field="email")
		return email or None

	@field_validator("phone")
	@classmethod
	def check_phone(cls, phone: str | None) -> str | None:
		if phone and not validate_phone_number(phone):
			InvalidCustomer.throw(field="phone")
		return phone or None


class HostedOrder(APIResponse):
	order_id: str
	checkout_url: str


class HostedRefund(APIResponse):
	refund_id: str
	status: str
	amount: float
