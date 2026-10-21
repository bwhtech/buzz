from typing import TYPE_CHECKING

import frappe
from frappe import _

from buzz.playground import main_event

if TYPE_CHECKING:
	from buzz.playground.doctype.playground_sandbox.playground_sandbox import PlaygroundSandbox


class PlaygroundChecklist:
	"""Getting-started steps, done once the sandbox holds a record the visitor made.

	Read from the sandbox's data rather than stored per user, so it is shared by all three personas.
	"""

	def __init__(self, sandbox: "PlaygroundSandbox"):
		self.sandbox = sandbox
		self.events = frappe.get_all("Buzz Event", {"team": sandbox.team}, pluck="name")
		self.event = main_event(sandbox.team)

	def steps(self) -> list[dict]:
		manage = f"/b/manage/events/{self.event.name}" if self.event else "/b/manage"
		event_page = f"/events/{self.event.route}" if self.event else "/events"
		return [
			self.step("add_ticket_type", _("Add a ticket type"), "organizer", f"{manage}/registrations"),
			self.step("book_ticket", _("Book a ticket as the attendee"), "attendee", event_page),
			self.step("check_in", _("Check a guest in at the front desk"), "front_desk", "/b/check-in"),
			self.step("email_guests", _("Email your guests"), "organizer", f"{manage}/communications"),
		]

	def step(self, name: str, title: str, persona: str, path: str) -> dict:
		return {
			"name": name,
			"title": title,
			"persona": persona,
			"path": path,
			"completed": self.is_completed(name),
		}

	def is_completed(self, name: str) -> bool:
		doctype, filters = {
			"add_ticket_type": ("Event Ticket Type", {"event": ["in", self.events]}),
			"book_ticket": ("Event Booking", {"user": self.sandbox.attendee, "docstatus": ["<", 2]}),
			"check_in": ("Event Check In", {"event": ["in", self.events]}),
			"email_guests": ("Event Communication", {"event": ["in", self.events]}),
		}[name]
		# Seeding finishes before the sandbox is saved, so only the visitor's records are newer.
		return bool(frappe.db.exists(doctype, {**filters, "creation": [">", self.sandbox.creation]}))
