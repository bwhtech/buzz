from datetime import date, timedelta

from buzz.api.schemas import APIResponse


class FormEventSummary(APIResponse):
	# Buzz Event autoincrements, so the raw name is an int; sent as a string so a naming
	# change on the doctype cannot break the response.
	name: str
	title: str
	route: str | None
	banner_image: str | None
	start_date: date
	end_date: date | None
	start_time: timedelta | None
	end_time: timedelta | None
	time_zone: str | None
	time_zone_label: str | None
	venue: str | None
	medium: str | None
	short_description: str | None


class CustomFieldDefinition(APIResponse):
	label: str
	fieldname: str | None
	fieldtype: str
	options: str | None
	mandatory: int
	placeholder: str | None
	default_value: str | None
	order: int


class CustomFormResponse(APIResponse):
	# Field shape varies per fieldtype at runtime, so only the envelope is modelled.
	form_fields: list[dict]
	custom_fields: list[CustomFieldDefinition]
	form_title: str
	event: FormEventSummary
	closed: bool
	closed_title: str
	closed_message: str
	success_title: str
	success_message: str


class EventProposalFormResponse(APIResponse):
	form_fields: list[dict]
	form_title: str
	banner_title: str
	success_title: str
	success_message: str
