import frappe
from frappe.utils import add_days, add_to_date, now_datetime, today

from buzz.events.doctype.buzz_team_settings.buzz_team_settings import feature_flags
from buzz.playground import is_playground, sandbox_of

CATEGORY = "Technology"
LOGO = "/assets/buzz/images/buzz-logo.png"
FIRST_NAMES = (
	"Priya",
	"Arjun",
	"Sara",
	"Rahul",
	"Ananya",
	"Vikram",
	"Meera",
	"Kabir",
	"Isha",
	"Dev",
	"Nisha",
)
LAST_NAMES = ("Sharma", "Mehta", "Khan", "Verma", "Iyer")
GUESTS = [(first, last) for last in LAST_NAMES for first in FIRST_NAMES]
PROPOSALS = (
	("Offline-first event check-in", "Leela", "Nair"),
	("What we learned running 40 meetups", "Tom", "Fischer"),
	("Accessible ticketing flows", "Aisha", "Bello"),
	("Postgres tricks for busy launches", "Marco", "Rossi"),
)
COMMUNITY_REQUESTS = (
	("FOSS Meetup Bengaluru", "FOSS United", "https://fossunited.org", 10),
	("Frappe Developer Meetup", "Frappe", "https://frappe.io", 21),
)


def insert(doctype: str, **fields):
	return frappe.get_doc({"doctype": doctype, **fields}).insert(ignore_permissions=True)


class DemoData:
	"""Gives a sandbox team a conference, a meetup and a past event to explore."""

	def __init__(self, team: str, organizer: str, attendee: str):
		self.team = team
		self.organizer = organizer
		self.attendee = attendee

	def create(self) -> str:
		frappe.flags.seeding_playground = True
		try:
			self.enable_features()
			category = frappe.get_doc({"doctype": "Event Category", "name": CATEGORY})
			category.insert(ignore_permissions=True, ignore_if_duplicate=True)
			self.host = insert("Event Host", host_name="Acme Community", team=self.team).name
			conference = self.create_conference()
			self.create_meetup()
			self.create_past_event()
		finally:
			frappe.flags.seeding_playground = False
		return conference

	def enable_features(self):
		settings = frappe.get_doc("Buzz Team Settings", self.team)
		settings.update(dict.fromkeys(feature_flags(self.team), 1))
		# No deck template exists, so each enquiry would only log an error trying to send one.
		# The event carries its own toggle as well; create_event turns that off.
		settings.auto_send_pitch_deck = 0
		settings.save(ignore_permissions=True)

	def create_event(self, title: str, days_from_today: int, **fields) -> str:
		event_date = add_days(today(), days_from_today)
		event = insert(
			"Buzz Event",
			title=title,
			team=self.team,
			host=self.host,
			category=CATEGORY,
			start_date=event_date,
			end_date=event_date,
			start_time="10:00:00",
			end_time="18:00:00",
			# New events start closed; demo guests book until the doors open.
			registrations_close_at=f"{event_date} 10:00:00",
			short_description=f"{title}, a Buzz Playground demo event.",
			auto_send_pitch_deck=0,
			**fields,
		).name
		# Replaced by the demo's own tiers.
		for doctype in ("Event Ticket Type", "Sponsorship Tier"):
			frappe.db.delete(doctype, {"event": event, "title": "Normal"})
		return event

	def create_conference(self) -> str:
		venue = insert(
			"Event Venue",
			venue_name="Bangalore International Centre",
			address="7, 4th Main Road, Domlur, Bengaluru",
			team=self.team,
		).name
		event = self.create_event("DevConf 2026", 30, medium="In Person", venue=venue)
		early_bird = self.ticket_type(event, "Early Bird", 499, max_tickets_available=2)
		regular = self.ticket_type(event, "Regular", 999)
		self.ticket_type(event, "VIP", 2499)
		insert(
			"Ticket Add-on",
			event=event,
			title="T-shirt",
			price=299,
			options="S\nM\nL\nXL",
			user_selects_option=1,
		)
		insert("Ticket Add-on", event=event, title="Workshop pass", price=499)
		insert(
			"Buzz Coupon Code",
			coupon_type="Discount",
			discount_type="Percentage",
			discount_value=20,
			event=event,
		)
		self.create_sponsors(event)
		self.create_talks(event)
		self.create_proposals(event)
		self.book(event, early_bird, GUESTS[:2], paid=True)
		# Five guests a booking gives the announcement step a full guest list.
		for start in range(2, len(GUESTS), 5):
			self.book(event, regular, GUESTS[start : start + 5], paid=True)
		self.book(event, regular, [("Sam", "Attendee")], paid=True, user=self.attendee)
		return event

	def create_meetup(self):
		event = self.create_event("Frontend Meetup", 14, medium="Online", meeting_link="https://bwh.tech")
		ticket_type = self.ticket_type(event, "Free", 0, max_tickets_available=50)
		self.book(event, ticket_type, GUESTS[3:9])

	def create_past_event(self):
		event = self.create_event("Open Source Day", -20, medium="Online", meeting_link="https://bwh.tech")
		tickets = self.book(event, self.ticket_type(event, "Free", 0), GUESTS[:4])
		for ticket in tickets[:3]:
			insert("Event Check In", event=event, ticket=ticket).submit()

	def ticket_type(self, event: str, title: str, price: int, **fields) -> str:
		prices = [{"currency": "INR", "price": price}] if price else []
		return insert("Event Ticket Type", event=event, title=title, prices=prices, **fields).name

	def create_sponsors(self, event: str):
		tier = insert(
			"Sponsorship Tier", event=event, title="Gold", prices=[{"currency": "INR", "price": 100000}]
		)
		insert("Event Sponsor", event=event, tier=tier.name, company_name="Globex", company_logo=LOGO)
		for company in ("Initech", "Umbrella Labs"):
			insert(
				"Sponsorship Enquiry", event=event, tier=tier.name, company_name=company, company_logo=LOGO
			)

	def create_proposals(self, event: str):
		for title, first_name, last_name in PROPOSALS:
			speaker = {
				"first_name": first_name,
				"last_name": last_name,
				"email": f"{first_name.lower()}@example.com",
			}
			# As the public form submits it. Left blank it would take the session user, which on a
			# reset is the previous sandbox's organizer, deleted right after.
			insert(
				"Talk Proposal",
				event=event,
				title=title,
				status="Review Pending",
				speakers=[speaker],
				submitted_by="Guest",
			)

	def create_talks(self, event: str):
		for title in ("Shipping with Frappe", "Designing for events", "Scaling ticket sales"):
			insert("Event Talk", event=event, title=title, submitted_by=self.organizer)

	def book(
		self, event: str, ticket_type: str, guests, paid: bool = False, user: str | None = None
	) -> list[str]:
		attendees = [
			{
				"ticket_type": ticket_type,
				"first_name": first,
				"last_name": last,
				"email": f"{first.lower()}.{last.lower()}@example.com",
			}
			for first, last in guests
		]
		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": event,
				"user": user or self.organizer,
				"attendees": attendees,
			}
		)
		if paid:
			booking.update({"payment_status": "Paid", "status": "Confirmed", "payment_method": "Playground"})
		booking.flags.ignore_permissions = True
		booking.insert()
		booking.submit()
		return frappe.get_all("Event Ticket", filters={"booking": booking.name}, pluck="name")


def seed_community_requests(team, method=None):
	"""A community the visitor creates gets event requests from other hosts to review."""
	if not (is_playground() and team.is_published and sandbox_of(frappe.session.user)):
		return
	for title, host, url, days_from_today in COMMUNITY_REQUESTS:
		starts_at = add_to_date(now_datetime(), days=days_from_today)
		insert(
			"Community Event Request",
			community=team.name,
			is_external_event=1,
			event_title=title,
			host=host,
			event_url=url,
			event_location="Bengaluru",
			start_datetime=starts_at,
			end_datetime=add_to_date(starts_at, hours=3),
		)
