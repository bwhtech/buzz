import frappe

from buzz.api.checkin.schemas import CheckinResponse
from buzz.api.checkin.services import CheckinService


@frappe.whitelist()
def validate_ticket_for_checkin(ticket_id: str) -> CheckinResponse:
	return CheckinService(ticket_id).validate()


@frappe.whitelist()
def checkin_ticket(ticket_id: str) -> CheckinResponse:
	return CheckinService(ticket_id).checkin()
