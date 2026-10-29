# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from frappe.utils.data import get_datetime, time_diff_in_seconds
from frappe.website.utils import cleanup_page_name

from buzz import telemetry
from buzz.api.forms.conditions import parse_rules
from buzz.events.doctype.buzz_form.condition_validator import ConditionValidator
from buzz.events.doctype.buzz_form.form_types import (
	QUESTION_FIELD_NAMES,
	create_default_forms,
	event_form,
	template_rules,
)
from buzz.events.doctype.buzz_team_settings.buzz_team_settings import get_team_settings
from buzz.events.doctype.event_check_in_zone.event_check_in_zone import create_default_zone
from buzz.ticketing.doctype.event_ticket_category.event_ticket_category import create_ticket_categories
from buzz.utils import get_time_zone_label, only_if_app_installed

# Top-level dashboard route segments (/b/<segment>) an event route must not shadow.
RESERVED_EVENT_ROUTES = {
	"account",
	"bookings",
	"booking-success",
	"tickets",
	"register",
	"register-interest",
	"check-in",
	"book-tickets",
	"event-proposal",
	"events",
	"manage",
	"playground",
}

MAX_TOPICS = 5


class BuzzEvent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buzz.events.doctype.event_cohost.event_cohost import EventCoHost
		from buzz.events.doctype.event_external_link.event_external_link import EventExternalLink
		from buzz.events.doctype.event_featured_speaker.event_featured_speaker import EventFeaturedSpeaker
		from buzz.events.doctype.event_payment_gateway.event_payment_gateway import EventPaymentGateway
		from buzz.events.doctype.event_topic_link.event_topic_link import EventTopicLink
		from buzz.proposals.doctype.sponsorship_deck_item.sponsorship_deck_item import SponsorshipDeckItem

		about: DF.TextEditor | None
		allow_editing_talks_after_acceptance: DF.Check
		allow_guest_booking: DF.Check
		apply_tax: DF.Check
		attach_calendar_invite: DF.Check
		attach_email_ticket: DF.Check
		auto_send_pitch_deck: DF.Check
		banner_image: DF.AttachImage | None
		booking_confirmation_email_template: DF.Link | None
		card_image: DF.AttachImage | None
		category: DF.Link
		co_hosts: DF.Table[EventCoHost]
		default_ticket_type: DF.Link | None
		end_date: DF.Date | None
		end_time: DF.Time
		external_links: DF.Table[EventExternalLink]
		external_registration_page: DF.Check
		featured_speakers: DF.Table[EventFeaturedSpeaker]
		free_event: DF.Check
		guest_verification_method: DF.Literal["None", "Email OTP", "Phone OTP"]
		host: DF.Link | None
		is_featured: DF.Check
		is_published: DF.Check
		medium: DF.Literal["In Person", "Online"]
		meeting_link: DF.Data | None
		meta_image: DF.AttachImage | None
		name: DF.Int | None
		offline_acknowledgement_email_template: DF.Link | None
		og_image: DF.AttachImage | None
		payment_gateways: DF.Table[EventPaymentGateway]
		proposal: DF.Link | None
		registration_url: DF.Data | None
		route: DF.Data | None
		send_booking_confirmation_email: DF.Check
		send_ticket_email: DF.Check
		short_description: DF.SmallText | None
		show_countdown: DF.Check
		show_sponsorship_section: DF.Check
		sponsor_deck_attachments: DF.Table[SponsorshipDeckItem]
		sponsor_deck_cc: DF.SmallText | None
		sponsor_deck_email_template: DF.Link | None
		sponsor_deck_reply_to: DF.Data | None
		start_date: DF.Date
		start_time: DF.Time
		tax_inclusive: DF.Check
		tax_label: DF.Data | None
		tax_percentage: DF.Percent
		team: DF.Link
		theme: DF.Link | None
		ticket_email_template: DF.Link | None
		ticket_print_format: DF.Link | None
		time_zone: DF.Autocomplete | None
		time_zone_label: DF.Data | None
		title: DF.Data
		topics: DF.TableMultiSelect[EventTopicLink]
		venue: DF.Link | None
	# end: auto-generated types

	def before_insert(self):
		if not self.route:
			self.route = self.make_route()
		self.add_default_payment_gateway()

	def add_default_payment_gateway(self):
		default = frappe.db.get_single_value("Buzz Settings", "default_payment_gateway")
		if default and not self.payment_gateways:
			self.append("payment_gateways", {"payment_gateway": default})

	def validate(self):
		self.validate_dates()
		self.validate_route()
		self.validate_tax_settings()
		self.validate_guest_verification_config()
		self.clear_unused_location()
		self.validate_co_hosts()
		self.validate_external_links()
		self.validate_topics()
		self.set_time_zone_label()

	def clear_unused_location(self):
		"""Only the medium in force keeps its location.

		`generate_ics_file` and the booking page both read `venue` without consulting
		`medium`, so a venue left behind by a switch to Online publishes an address the
		event no longer has.
		"""
		if self.medium == "Online":
			self.venue = None
		else:
			self.meeting_link = None

	def get_venue_name(self) -> str | None:
		return frappe.get_cached_value("Event Venue", self.venue, "venue_name") if self.venue else None

	def validate_co_hosts(self):
		hosts = [row.host for row in self.co_hosts]
		duplicate = next((host for host in hosts if hosts.count(host) > 1), None)
		if duplicate:
			label = frappe.db.get_value("Event Host", duplicate, "host_name") or duplicate
			frappe.throw(_("{0} is already a co-host of this event.").format(label))

	def validate_external_links(self):
		for row in self.external_links:
			if urlparse(row.url or "").scheme not in ("http", "https"):
				frappe.throw(_("Row {0}: link must start with http:// or https://").format(row.idx))

	def validate_topics(self):
		if len(self.topics) > MAX_TOPICS:
			frappe.throw(_("An event can have at most {0} topics.").format(MAX_TOPICS))

	def set_time_zone_label(self):
		# validate runs before the mandatory check, so dates may still be empty here
		if not (self.time_zone and self.start_date and self.start_time):
			self.time_zone_label = ""
			return

		# computed at event start so DST zones get the abbreviation in effect then
		event_start = get_datetime(f"{self.start_date} {self.start_time}")
		self.time_zone_label = get_time_zone_label(self.time_zone, event_start)

	def validate_dates(self):
		self.validate_from_to_dates("start_date", "end_date")
		if (
			(not self.end_date or self.start_date == self.end_date)
			and self.start_time
			and self.end_time
			and time_diff_in_seconds(self.end_time, self.start_time) <= 0
		):
			frappe.throw(frappe._("<b>End Time</b> must be after <b>Start Time</b>"))

	def validate_tax_settings(self):
		"""Set default tax values when tax is enabled."""
		if self.apply_tax:
			if not self.tax_label:
				self.tax_label = "GST"
			if not self.tax_percentage:
				self.tax_percentage = 18
			if not 0 <= self.tax_percentage <= 100:
				frappe.throw(_("Tax rate must be between 0 and 100"))

	def validate_route(self):
		if self.is_published and not self.route:
			self.route = self.make_route()

		# Compared lowercased: vue-router matches paths case-insensitively, so a
		# route like "Account" shadows /b/account just as "account" would.
		if (self.route or "").lower() in RESERVED_EVENT_ROUTES:
			frappe.throw(
				_("'{0}' is a reserved route and cannot be used as an event route.").format(self.route)
			)

	def make_route(self):
		# Room for the "-<n>" suffix within the 140-char Data field.
		slug = cleanup_page_name(self.title).replace("_", "-")[:130].strip("-")
		if not slug or slug in RESERVED_EVENT_ROUTES:
			slug = f"{slug}-event".lstrip("-")
		return append_number_if_name_exists("Buzz Event", slug, fieldname="route")

	def validate_guest_verification_config(self):
		"""Ensure email/SMS is configured when OTP verification is enabled."""
		if frappe.in_test or not self.allow_guest_booking:
			return

		# Imported here rather than at the top: doctype modules load during boot, and this
		# pulls frappe.email onto that path for a check only these branches make.
		from buzz.api.booking.guests import email_otp_available, phone_otp_available

		if self.guest_verification_method == "Email OTP" and not email_otp_available():
			frappe.throw(
				_("Please configure an outgoing Email Account before enabling Email OTP verification."),
				title=_("Email Not Configured"),
			)

		if self.guest_verification_method == "Phone OTP" and not phone_otp_available():
			frappe.throw(
				_(
					"Please configure SMS Settings, and allow the Guest role to send SMS, "
					"before enabling Phone OTP verification."
				),
				title=_("SMS Not Configured"),
			)

	def after_insert(self):
		self.create_default_records()
		self.capture_created()
		if self.is_published:
			self.capture_published()

	def capture_created(self):
		if self.proposal:
			source = "proposal"
		elif self.flags.from_template:
			source = "template"
		else:
			source = "blank"

		telemetry.capture(
			"event_created",
			{
				"source": source,
				"medium": self.medium,
				"free_event": bool(self.free_event),
				"published": bool(self.is_published),
			},
		)

	def on_trash(self):
		# Forms are created with the event, so they go with it. Frappe runs this before the
		# link check, which would otherwise refuse every event delete. Enquiries block the
		# delete on their own link to the event, so leave their forms standing rather than
		# pre-empting that with a worse message.
		if not frappe.db.exists("Sponsorship Enquiry", {"event": self.name}):
			for form in frappe.get_all("Buzz Form", {"event": self.name}, pluck="name"):
				frappe.delete_doc("Buzz Form", form, ignore_permissions=True)
		self.enqueue_listing_share_images()
		# A community's request to list the event means nothing once the event is gone.
		frappe.db.delete("Community Event Request", {"event": self.name})
		# Zones come with the event, the default one included. Check-ins block the delete on
		# their own link to the event, so the zones stay while any exist.
		if not frappe.db.exists("Event Check In", {"event": self.name}):
			for zone in frappe.get_all("Event Check-in Zone", {"event": self.name}, pluck="name"):
				frappe.delete_doc("Event Check-in Zone", zone, ignore_permissions=True, ignore_on_trash=True)

	def enqueue_listing_share_images(self):
		from buzz.events.community_og_image import enqueue_generate_for

		enqueue_generate_for(self.team)
		for community in frappe.get_all("Community Event Request", {"event": self.name}, pluck="community"):
			enqueue_generate_for(community)

	def create_default_records(self):
		records = [
			{"doctype": "Sponsorship Tier", "title": "Normal", "prices": [{"price": 0}]},
			{"doctype": "Event Ticket Type", "title": "Normal"},
		]
		for record in records:
			frappe.get_doc({**record, "event": self.name}).insert(ignore_permissions=True)
		create_default_forms(self.name)
		create_default_zone(self.name)

	def archive_event(self):
		"""Take the event off the public site, along with the forms and registrations it takes.

		The booking and form gates already refuse an unpublished event; this is the stored
		state catching up, so publishing again does not reopen everything with it.
		"""
		self.is_published = 0
		for name in frappe.get_all("Buzz Form", {"event": self.name}, pluck="name"):
			form = frappe.get_doc("Buzz Form", name)
			form.flags.ignore_permissions = True
			form.set_closed(True)
		self.save()

	@frappe.whitelist()
	@only_if_app_installed("zoom_integration", raise_exception=True)
	def create_webinar_on_zoom(self):
		if not self.end_time:
			frappe.throw(frappe._("End time is needed for Zoom Webinar creation"))

		zoom_webinar = frappe.get_doc(
			{
				"doctype": "Zoom Webinar",
				"title": self.title,
				"date": self.start_date,
				"start_time": self.start_time,
				"duration": int(time_diff_in_seconds(self.end_time, self.start_time)),
				"timezone": self.time_zone,
				"template": get_team_settings(self.team).default_webinar_template,
			}
		).insert()

		self.db_set("zoom_webinar", zoom_webinar.name)

		return zoom_webinar

	@frappe.whitelist()
	@only_if_app_installed("zoom_integration", raise_exception=True)
	def create_meeting_on_zoom(self):
		if not self.end_time:
			frappe.throw(_("End time is needed for Zoom Meeting creation"))

		zoom_meeting = frappe.get_doc(
			{
				"doctype": "Zoom Meeting",
				"title": self.title,
				"date": self.start_date,
				"start_time": self.start_time,
				"duration": int(time_diff_in_seconds(self.end_time, self.start_time)),
				"timezone": self.time_zone,
			}
		).insert()

		self.db_set("zoom_meeting", zoom_meeting.name)

		return zoom_meeting

	def on_update(self):
		self.update_zoom_webinar()
		self.update_zoom_meeting()
		self.capture_published_change()
		self.enqueue_og_image()
		self.enqueue_team_share_images()

	def enqueue_team_share_images(self):
		"""A team's share image counts its events."""
		from buzz.events.community_og_image import enqueue_generate_for

		enqueue_generate_for(self.team)

	def enqueue_og_image(self):
		from buzz.events.og_image import EventOgImage, enqueue_generate

		# A live worker would render test events mid-test and race their teardown
		if frappe.in_test or not (self.is_published and self.route):
			return
		try:
			needs_update = EventOgImage(self).needs_update()
		except Exception:
			# The share image is a nicety; it must never block saving the event
			frappe.log_error(f"Share image check failed for event {self.name}")
			return
		if needs_update:
			enqueue_generate(str(self.name))

	def capture_published_change(self):
		if not self.flags.in_insert and self.is_published and self.has_value_changed("is_published"):
			self.capture_published()

	def capture_published(self):
		telemetry.capture("event_published", {"medium": self.medium, "free_event": bool(self.free_event)})

	@only_if_app_installed("zoom_integration")
	def update_zoom_webinar(self):
		if not self.zoom_webinar:
			return

		if (
			self.has_value_changed("start_date")
			or self.has_value_changed("end_time")
			or self.has_value_changed("start_time")
			or self.has_value_changed("time_zone")
		):
			webinar = frappe.get_doc("Zoom Webinar", self.zoom_webinar)
			webinar.update(
				{
					"date": self.start_date,
					"start_time": self.start_time,
					"duration": int(time_diff_in_seconds(self.end_time, self.start_time)),
					"timezone": self.time_zone,
				}
			)
			webinar.save()

	@only_if_app_installed("zoom_integration")
	def update_zoom_meeting(self):
		if not self.zoom_meeting:
			return

		if (
			self.has_value_changed("start_date")
			or self.has_value_changed("end_time")
			or self.has_value_changed("start_time")
			or self.has_value_changed("time_zone")
		):
			meeting = frappe.get_doc("Zoom Meeting", self.zoom_meeting)
			meeting.update(
				{
					"date": self.start_date,
					"start_time": self.start_time,
					"duration": int(time_diff_in_seconds(self.end_time, self.start_time)),
					"timezone": self.time_zone,
				}
			)
			meeting.save()


@frappe.whitelist()
def create_from_template(template_name: str, options: str, additional_fields: str = "{}") -> str:
	"""
	Create a new Buzz Event from a template.

	Args:
	    template_name: Name of the Event Template
	    options: JSON string of what to copy (e.g., {"category": 1, "ticket_types": 1, ...})
	    additional_fields: JSON string of additional field values for mandatory fields not in template

	Returns:
	    New Buzz Event document name
	"""
	if not frappe.has_permission("Event Template", "read"):
		frappe.throw(_("You don't have permission to use templates"))

	if not frappe.has_permission("Buzz Event", "create"):
		frappe.throw(_("You don't have permission to create events"))

	template = frappe.get_doc("Event Template", template_name)
	options = frappe.parse_json(options)
	additional_fields = frappe.parse_json(additional_fields)

	# Create new event with required fields
	event = frappe.new_doc("Buzz Event")
	event.title = f"New Event from {template.template_name}"
	event.start_date = frappe.utils.today()
	event.start_time = "09:00:00"
	event.end_time = "18:00:00"
	event.flags.from_template = True

	# Apply additional fields first (these are mandatory fields provided by user)
	for field, value in additional_fields.items():
		if value:
			event.set(field, value)

	# Field mapping for direct copy
	field_map = {
		"category": "category",
		"host": "host",
		"banner_image": "banner_image",
		"short_description": "short_description",
		"about": "about",
		"medium": "medium",
		"venue": "venue",
		"allow_guest_booking": "allow_guest_booking",
		"guest_verification_method": "guest_verification_method",
		"time_zone": "time_zone",
		"send_ticket_email": "send_ticket_email",
		"ticket_email_template": "ticket_email_template",
		"ticket_print_format": "ticket_print_format",
		"apply_tax": "apply_tax",
		"tax_inclusive": "tax_inclusive",
		"tax_label": "tax_label",
		"tax_percentage": "tax_percentage",
		"auto_send_pitch_deck": "auto_send_pitch_deck",
		"sponsor_deck_email_template": "sponsor_deck_email_template",
		"sponsor_deck_reply_to": "sponsor_deck_reply_to",
		"sponsor_deck_cc": "sponsor_deck_cc",
	}

	for option_key, field_name in field_map.items():
		if options.get(option_key):
			event.set(field_name, template.get(field_name))

	# Copy child tables
	if options.get("payment_gateways"):
		for pg in template.payment_gateways:
			event.append("payment_gateways", {"payment_gateway": pg.payment_gateway})

	if options.get("sponsor_deck_attachments"):
		for attachment in template.sponsor_deck_attachments:
			event.append("sponsor_deck_attachments", {"file": attachment.file})

	event.insert()

	# Create linked documents (Ticket Types, Add-ons, Custom Fields)
	if options.get("ticket_types"):
		category_names = create_ticket_categories(event.name, template.template_ticket_categories)
		for tt in template.template_ticket_types:
			ticket_type = frappe.new_doc("Event Ticket Type")
			ticket_type.event = event.name
			ticket_type.title = tt.title
			ticket_type.category = category_names.get(tt.category)
			ticket_type.append("prices", {"currency": tt.currency, "price": tt.price})
			ticket_type.is_published = tt.is_published
			ticket_type.max_tickets_available = tt.max_tickets_available
			ticket_type.auto_unpublish_after = tt.auto_unpublish_after
			ticket_type.insert()

	if options.get("add_ons"):
		for addon in template.template_add_ons:
			add_on = frappe.new_doc("Ticket Add-on")
			add_on.event = event.name
			add_on.title = addon.title
			add_on.price = addon.price
			add_on.currency = addon.currency
			add_on.description = addon.description
			add_on.user_selects_option = addon.user_selects_option
			add_on.options = addon.options
			add_on.enabled = addon.enabled
			add_on.insert()

	if options.get("custom_fields"):
		copy_template_questions(event, template.template_custom_fields)

	return event.name


def copy_template_questions(event, template_fields):
	"""A template may name a form this event has not got; its questions are dropped."""
	forms = {}
	for field in template_fields:
		if field.form_doctype not in forms:
			forms[field.form_doctype] = event_form(event.name, field.form_doctype)
		if form := forms[field.form_doctype]:
			form.append("questions", {name: field.get(name) for name in QUESTION_FIELD_NAMES})
			rules = parse_rules(form.logic_rules) + template_rules(field)
			form.logic_rules = frappe.as_json(rules, indent=None) if rules else None
	for form in forms.values():
		if form:
			ConditionValidator(form).drop_link_conditions()
			form.save(ignore_permissions=True)
