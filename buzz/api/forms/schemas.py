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
	description: str | None = None
	width: str | None = "Full"
	order: int


class CustomFormResponse(APIResponse):
	submission_method: str | None = None
	# Field shape varies per fieldtype at runtime, so only the envelope is modelled.
	form_fields: list[dict]
	custom_fields: list[CustomFieldDefinition]
	# Show, hide and require rules over the questions; the server applies them again on submit.
	logic_rules: list | None = None
	form_title: str
	form_description: str | None = None
	submit_label: str | None = None
	event: FormEventSummary
	closed: bool
	closed_title: str
	closed_message: str
	success_title: str
	success_message: str
	redirect_url: str | None = None


class EventProposalFormResponse(APIResponse):
	form_fields: list[dict]
	form_title: str
	banner_title: str
	success_title: str
	success_message: str


class DoctypeField(APIResponse):
	"""A field of the form's doctype: a core row when offered, and a name conditions may test."""

	fieldname: str
	fieldtype: str
	label: str
	options: str | None = None
	link_options: list[dict] | None = None
	offered: bool
	locked: bool


class FormBuilderFields(APIResponse):
	fields: list[DoctypeField]
	# The registration form is edited beside the event's attendee form.
	attendee_form: str | None = None
