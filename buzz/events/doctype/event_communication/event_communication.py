# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_url

from buzz.api.communications.exceptions import NoRecipients
from buzz.api.communications.services import recipients_of
from buzz.api.events.services import registration_link
from buzz.events.doctype.buzz_team_settings.buzz_team_settings import get_event_team_settings
from buzz.utils import build_event_datetimes, get_time_zone_label

TEMPLATE = "buzz/templates/emails/event_communication.html"
LOGO = "/assets/buzz/images/buzz-logo-rounded.png"


class EventCommunication(Document):
	def validate(self):
		self.recipients = recipients_of(self.event, self.audience, self.ticket_types, self.statuses)
		self.recipient_count = len(self.recipients)
		if not self.recipient_count:
			NoRecipients.throw()

	def after_insert(self):
		event = frappe.get_cached_doc("Buzz Event", self.event)
		frappe.sendmail(
			recipients=self.recipients,
			subject=self.subject or event.title,
			message=self.render(event),
			# No team support address yet: replies reach whoever pressed Send.
			reply_to=get_event_team_settings(self.event).support_email or self.owner,
			reference_doctype=self.doctype,
			reference_name=self.name,
			send_after=self.scheduled_at,
			queue_separately=True,
			add_unsubscribe_link=0,
		)

	def render(self, event) -> str:
		link = registration_link(event)
		return frappe.render_template(
			TEMPLATE,
			{
				"event_title": event.title,
				"when": event_when(event),
				"venue": event.venue,
				"banner_url": get_url(event.banner_image) if event.banner_image else None,
				"event_url": get_url(link) if link else None,
				"logo_url": get_url(LOGO),
				"message": self.message,
			},
		)


def event_when(event) -> str:
	"""'Sep 2, 3:30 PM IST' — the date, the start time, and the zone it is in."""
	start, _ = build_event_datetimes(event)
	label = get_time_zone_label(event.time_zone, start)
	when = start.strftime("%b %-d, %-I:%M %p")
	return f"{when} {label}" if label else when
