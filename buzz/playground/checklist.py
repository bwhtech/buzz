from typing import TYPE_CHECKING

import frappe
from frappe import _

from buzz.api.booking.services import are_registrations_closed
from buzz.api.proposals.services import are_proposals_closed
from buzz.playground import main_event, sandbox_teams
from buzz.playground.demo_data import COMMUNITY_REQUESTS, PROPOSALS

if TYPE_CHECKING:
	from buzz.playground.doctype.playground_sandbox.playground_sandbox import PlaygroundSandbox


class PlaygroundChecklist:
	"""Getting-started tasks, done once the sandbox holds a record the visitor made.

	Read from the sandbox's data rather than stored per user, so it is shared by all three personas.
	Seeding finishes before the sandbox is saved, so records newer than the sandbox are the visitor's.
	"""

	def __init__(self, sandbox: "PlaygroundSandbox"):
		self.sandbox = sandbox
		self.team = sandbox.team
		teams = sandbox_teams(sandbox)
		self.events = frappe.get_all("Buzz Event", {"team": ["in", teams]}, pluck="name")
		self.conference = main_event(sandbox)
		self.own_event = frappe.db.get_value(
			"Buzz Event",
			{"team": ["in", teams], "creation": [">", sandbox.creation]},
			order_by="creation desc",
		)
		self.community = frappe.db.get_value(
			"Buzz Team",
			{
				"name": ["in", teams],
				"is_published": 1,
				"is_personal": 0,
				"creation": [">", sandbox.creation],
			},
			order_by="creation desc",
		)

	def groups(self) -> list[dict]:
		return [
			self.launch_group(),
			self.attendee_group(),
			self.conference_group(),
			self.sponsor_group(),
			self.community_group(),
			self.collaborator_group(),
		]

	def launch_group(self) -> dict:
		event = self.own_event
		manage = f"/b/manage/events/{event}"
		doc = event and frappe.get_doc("Buzz Event", event)
		steps = [
			self.step(
				"add_ticket_type",
				_("Add a ticket type"),
				_("Open Registrations and add a ticket type beside the default one."),
				f"{manage}/registrations",
				# The event comes with a default ticket type.
				event and frappe.db.count("Event Ticket Type", {"event": event}) > 1,
				target="Add ticket type",
			),
			self.step(
				"add_ticket_category",
				_("Group tickets into a category"),
				_("In Registrations, add a category and move a ticket type into it."),
				f"{manage}/registrations",
				event and self.exists("Event Ticket Category", event=event),
				optional=True,
				target="New Category",
			),
			self.step(
				"open_registrations",
				_("Open registrations"),
				_("New events start closed. Open registrations from the Registrations tab."),
				f"{manage}/registrations",
				doc and not are_registrations_closed(doc),
				target="Registration Closed",
			),
			self.step(
				"open_proposals",
				_("Open talk proposals"),
				_("Open the Talks tab and start taking proposals."),
				f"{manage}/talks",
				doc and not are_proposals_closed(doc),
				target="Proposals Closed",
			),
			self.step(
				"add_event_page",
				_("Add an extra page"),
				_("In Details, add a page such as a venue guide or FAQ."),
				f"{manage}/details",
				event and self.exists("Additional Event Page", event=event),
				optional=True,
				target="FAQ",
			),
		]
		for step in steps:
			step["locked"] = not event
		create = self.step(
			"create_event",
			_("Create an event"),
			_("Start your own event. The next steps set it up."),
			"/b/manage/team/events/new",
			bool(event),
			target="Name your event",
		)
		return self.group("launch", _("Launch your event"), [create, *steps])

	def attendee_group(self) -> dict:
		event_page = f"/events/{self.conference.route}"
		steps = [
			self.step(
				"browse_events",
				_("Browse upcoming events"),
				_("See what a guest finds on the events listing."),
				"/events",
				False,
				persona="attendee",
				completes_on="visit",
			),
			self.step(
				"view_event_page",
				_("Open an event page"),
				_("Schedule, speakers, sponsors and tickets, as a guest sees them."),
				event_page,
				False,
				persona="attendee",
				completes_on="visit",
			),
			self.step(
				"book_ticket",
				_("Book a ticket"),
				_("Pick a ticket and pay. Payments run in test mode."),
				event_page,
				self.added("Event Booking", user=self.sandbox.attendee, docstatus=["<", 2]),
				persona="attendee",
				target=_("Book more tickets"),
			),
		]
		return self.group("attendee", _("Attend as a guest"), steps)

	def conference_group(self) -> dict:
		conference = self.conference
		manage = f"/b/manage/events/{conference.name}"
		proposals = frappe.get_all("Talk Proposal", {"event": conference.name}, pluck="name")
		steps = [
			self.step(
				"accept_proposal",
				_("Accept a talk proposal"),
				_("Open a proposal in Talks and accept it. It joins the schedule."),
				f"{manage}/talks",
				self.exists("Talk Proposal", event=conference.name, status="Accepted"),
				target=_("Open {0}").format(PROPOSALS[0][0]),
			),
			self.step(
				"email_speaker",
				_("Email a speaker"),
				_("On a proposal, write a note and send it to the speaker by email."),
				f"{manage}/talks",
				self.exists(
					"Communication",
					reference_doctype="Talk Proposal",
					reference_name=["in", proposals],
					communication_type="Communication",
				),
				optional=True,
				target=_("Open {0}").format(PROPOSALS[0][0]),
			),
			self.step(
				"email_guests",
				_("Send an announcement"),
				_("Write to every guest from Communications. Emails land in the inbox."),
				f"{manage}/communications",
				self.added("Event Communication", event=["in", self.events]),
				target="Recipients",
			),
			self.step(
				"check_in",
				_("Check a guest in"),
				_("Scan or search a ticket at the front desk."),
				"/b/check-in",
				self.added("Event Check In", event=["in", self.events]),
				persona="front_desk",
				target=self.conference.title,
			),
			self.step(
				"add_tax_details",
				_("Add tax details"),
				_("Legal name and tax ID go on invoices."),
				f"/b/manage/communities/{self.team}/payments",
				self.exists("Buzz Team Settings", name=self.team, tax_id=["is", "set"]),
				optional=True,
			),
		]
		return self.group(
			"conference",
			_("Run {0}").format(frappe.db.get_value("Buzz Event", conference.name, "title")),
			steps,
		)

	def sponsor_group(self) -> dict:
		event = self.conference.name
		path = f"/b/manage/events/{event}/sponsorships"
		steps = [
			self.step(
				"open_tier",
				_("Open a sponsorship tier"),
				_("Open Gold to see what a tier holds: prices per currency, perks and how many are left."),
				path,
				False,
				completes_on="click",
				target="Gold",
			),
			self.step(
				"add_tier",
				_("Add a sponsorship tier"),
				_("Gold is set up. Add another tier with its price and perks."),
				path,
				self.added("Sponsorship Tier", event=event),
				target="Add Tier",
			),
			self.step(
				"add_sponsor",
				_("Add a sponsor"),
				_("Add a company to a tier by hand."),
				path,
				self.added("Event Sponsor", event=event),
				target="Add Manually",
			),
			self.step(
				"review_enquiry",
				_("Review a sponsor enquiry"),
				_("Two companies asked to sponsor. Approve one."),
				path,
				self.exists("Sponsorship Enquiry", event=event, status=["!=", "Approval Pending"]),
				optional=True,
				target="Initech",
			),
		]
		return self.group("sponsors", _("Bring in sponsors"), steps)

	def community_group(self) -> dict:
		community = self.community
		calendar_path = f"/b/manage/communities/{community}/calendar"
		seeded_titles = [request[0] for request in COMMUNITY_REQUESTS]
		steps = [
			self.step(
				"add_member",
				_("Add a team member"),
				_(
					"Invite a teammate by email and pick their role. The role decides what they can change, from running the whole community to only checking guests in."
				),
				f"/b/manage/communities/{community}/members",
				community and self.has_teammate(community),
				target=_("Add member"),
			),
			self.step(
				"approve_request",
				_("Approve an event request"),
				_("Other hosts asked to list events on your community. Approve one."),
				calendar_path,
				community
				and self.exists(
					"Community Event Request",
					community=community,
					status="Approved",
					event_title=["in", seeded_titles],
				),
				target=_("Approve"),
			),
			self.step(
				"add_external_event",
				_("Add an event from elsewhere"),
				_("List an event hosted on another site."),
				calendar_path,
				community
				and self.exists(
					"Community Event Request",
					community=community,
					is_external_event=1,
					event_title=["not in", seeded_titles],
				),
				optional=True,
				target=_("Add Event"),
			),
			self.step(
				"view_community_page",
				_("See your community page"),
				_("Your events and the ones you approved, on one public page."),
				f"/community/{community and frappe.db.get_value('Buzz Team', community, 'slug')}",
				False,
				completes_on="visit",
			),
		]
		for step in steps:
			step["locked"] = not community
		create = self.step(
			"create_community",
			_("Create a community"),
			_(
				"A community is your public page: your events, plus ones other hosts ask to list with you. Pick a URL and a name to make yours."
			),
			"/community",
			bool(community),
			target=_("Create a community"),
		)
		return self.group("community", _("Grow your community"), [create, *steps])

	def collaborator_group(self) -> dict:
		steps = [
			self.step(
				"invite_collaborator",
				_("Invite a collaborator"),
				_(
					"Give someone outside your team access to parts of one event, such as talks or check-in, without making them a team member."
				),
				f"/b/manage/events/{self.conference.name}/settings",
				self.exists("Buzz Event Collaborator", event=self.conference.name),
				target=_("Invite collaborator"),
			),
		]
		return self.group("collaborators", _("Work with collaborators"), steps)

	def group(self, name: str, title: str, steps: list[dict]) -> dict:
		return {"name": name, "title": title, "steps": steps}

	def step(
		self,
		name: str,
		title: str,
		description: str,
		path: str,
		completed,
		persona: str = "organizer",
		optional: bool = False,
		completes_on: str | None = None,
		target: str | None = None,
	) -> dict:
		return {
			"name": name,
			"title": title,
			"description": description,
			"persona": persona,
			"path": path,
			"completed": bool(completed),
			"optional": optional,
			"locked": False,
			"completes_on": completes_on,
			# Label of the control the spotlight points at, matched as a prefix.
			"target": target,
		}

	def has_teammate(self, community: str) -> bool:
		"""Someone besides the organizer joined, or was invited to, the community."""
		return self.exists(
			"Buzz Team Membership", team=community, user=["!=", self.sandbox.organizer]
		) or self.exists("User Invitation", buzz_team=community, app_name="buzz")

	def exists(self, doctype: str, **filters) -> bool:
		return bool(frappe.db.exists(doctype, filters))

	def added(self, doctype: str, **filters) -> bool:
		return self.exists(doctype, creation=[">", self.sandbox.creation], **filters)
