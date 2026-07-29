from typing import Any

from buzz.api.schemas import APIResponse


class TicketAddOnDetail(APIResponse):
	id: str
	name: str
	title: str | None
	value: str | None
	price: float | None
	currency: str | None
	user_selects_option: int | None
	options: list[str]


class TicketDetailsResponse(APIResponse):
	# doc, event, booking and ticket_type are whole documents; typing them would reshape
	# the payload, so they pass through as-is.
	doc: Any
	add_ons: list[TicketAddOnDetail]
	event: Any
	booking: Any | None
	ticket_type: Any
	can_transfer_ticket: bool
	can_change_add_ons: bool
	can_request_cancellation: bool
	zoom_join_url: str | None
	zoom_reference_doctype: str | None
	zoom_reference_name: str | None
