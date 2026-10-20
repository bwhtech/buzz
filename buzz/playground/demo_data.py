import frappe
from frappe.utils import add_days, today

from buzz.events.doctype.buzz_team_settings.buzz_team_settings import feature_flags

CATEGORY = "Technology"
LOGO = "/assets/buzz/images/buzz-logo.png"
GUESTS = [
	("Priya", "Sharma"),
	("Arjun", "Mehta"),
	("Sara", "Khan"),
	("Rahul", "Verma"),
	("Ananya", "Iyer"),
	("Vikram", "Rao"),
]


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
		settings.save(ignore_permissions=True)

	def create_event(self, title: str, days_from_today: int, **fields) -> str:
		if not frappe.db.exists("Event Category", CATEGORY):
			insert("Event Category", name=CATEGORY)
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
		self.book(event, early_bird, GUESTS[:2], paid=True)
		self.book(event, regular, GUESTS[2:5], paid=True)
		self.book(event, regular, [("Sam", "Attendee")], paid=True, user=self.attendee)
		return event

	def create_meetup(self):
		event = self.create_event(
			"Frontend Meetup", 14, medium="Online", meeting_link="https://meet.example.com/buzz"
		)
		ticket_type = self.ticket_type(event, "Free", 0, max_tickets_available=50)
		self.book(event, ticket_type, GUESTS[3:])

	def create_past_event(self):
		event = self.create_event(
			"Open Source Day", -20, medium="Online", meeting_link="https://meet.example.com/osd"
		)
		tickets = self.book(event, self.ticket_type(event, "Free", 0), GUESTS[:4])
		for ticket in tickets[:3]:
			insert("Event Check In", event=event, ticket=ticket).submit()

	def ticket_type(self, event: str, title: str, price: int, **fields) -> str:
		prices = [{"currency": "INR", "price": price}] if price else []
		return insert("Event Ticket Type", event=event, title=title, prices=prices, **fields).name

	def create_sponsors(self, event: str):
		for tier_title, price, company in (("Gold", 100000, "Globex"), ("Silver", 50000, "Initech")):
			tier = insert(
				"Sponsorship Tier",
				event=event,
				title=tier_title,
				prices=[{"currency": "INR", "price": price}],
			)
			insert("Event Sponsor", event=event, tier=tier.name, company_name=company, company_logo=LOGO)

	def create_talks(self, event: str):
		for title in ("Shipping with Frappe", "Designing for events", "Scaling ticket sales"):
			insert("Event Talk", event=event, title=title, submitted_by=self.organizer)

	def book(
		self, event: str, ticket_type: str, guests, paid: bool = False, user: str | None = None
	) -> list[str]:
		attendees = [
			{"ticket_type": ticket_type, "first_name": first, "last_name": last, "email": self.email(first)}
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

	def email(self, first_name: str) -> str:
		return f"{first_name.lower()}@example.com"
