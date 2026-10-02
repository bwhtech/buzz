import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.events import get_event_ticket_types, save_event_ticket_types
from buzz.api.events.exceptions import CannotManageEvent, TicketTypeHasSales, TicketTypeNotFound
from buzz.api.events.schemas import TicketTypeInput, TicketTypePriceInput
from buzz.api.events.test_events import create_event
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user
from buzz.test_permissions import add_member


class TicketTypesTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.owner = create_user("ticket-types-owner@example.com", "Owner")
		cls.viewer = create_user("ticket-types-viewer@example.com", "Viewer")
		cls.stranger = create_user("ticket-types-stranger@example.com", "Stranger")
		cls.team = create_owned_team("Ticket Types Team", cls.owner)
		add_member(cls.team, cls.viewer, "Viewer")

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")
		self.event = create_event("Ticket Types Event", self.team)
		self.ticket_type = self.make_ticket_type("General admission", price=1000, seats=200)

	def make_ticket_type(self, title, price=0, seats=0, event=None):
		return str(
			frappe.get_doc(
				{
					"doctype": "Event Ticket Type",
					"event": event or self.event,
					"title": title,
					"prices": [{"currency": "INR", "price": price}],
					"max_tickets_available": seats,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def sell(self, currency="INR"):
		frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.event,
				"user": "Administrator",
				"currency": currency,
				"payment_status": "Paid",
				"attendees": [
					{"ticket_type": self.ticket_type, "first_name": "Buyer", "email": "buyer@example.com"}
				],
			}
		).insert(ignore_permissions=True).submit()

	def save_as(self, user, ticket_types):
		frappe.set_user(user)
		return save_event_ticket_types(self.event, ticket_types).__json__()

	def current_input(self, **overrides):
		values = {
			"name": self.ticket_type,
			"title": "General admission",
			"prices": [inr(1000)],
			"max_tickets_available": 200,
		}
		return TicketTypeInput(**(values | overrides))


class TestGetEventTicketTypes(TicketTypesTestCase):
	def test_lists_ticket_types_with_tickets_sold(self):
		self.sell()
		frappe.set_user(self.owner)

		payload = get_event_ticket_types(self.event).__json__()

		self.assertTrue(payload["can_write"])
		row = next(row for row in payload["ticket_types"] if row["name"] == self.ticket_type)
		self.assertEqual(row["name"], self.ticket_type)
		self.assertEqual(row["prices"], [{"currency": "INR", "price": 1000, "tickets_sold": 1}])
		self.assertEqual(row["max_tickets_available"], 200)
		self.assertEqual(row["tickets_sold"], 1)

	def test_viewer_reads_without_write_access(self):
		frappe.set_user(self.viewer)

		payload = get_event_ticket_types(self.event).__json__()

		self.assertFalse(payload["can_write"])

	def test_stranger_cannot_read(self):
		frappe.set_user(self.stranger)

		with self.assertRaises(CannotManageEvent):
			get_event_ticket_types(self.event)


class TestSaveEventTicketTypes(TicketTypesTestCase):
	def test_updates_creates_and_deletes_in_one_save(self):
		removed = self.make_ticket_type("Early bird")

		payload = self.save_as(
			self.owner,
			[
				self.current_input(title="General", max_tickets_available=250),
				TicketTypeInput(title="Workshop pass", prices=[inr(2500)], max_tickets_available=30),
			],
		)

		titles = [row["title"] for row in payload["ticket_types"]]
		self.assertEqual(titles, ["General", "Workshop pass"])
		self.assertEqual(
			frappe.db.get_value("Event Ticket Type", self.ticket_type, "max_tickets_available"), 250
		)
		self.assertFalse(frappe.db.exists("Event Ticket Type", removed))
		created = frappe.get_doc("Event Ticket Type", payload["ticket_types"][1]["name"])
		self.assertEqual([(row.currency, row.price) for row in created.prices], [("INR", 2500)])

	def test_viewer_cannot_save(self):
		with self.assertRaises(CannotManageEvent):
			self.save_as(self.viewer, [self.current_input(title="Renamed")])

	def test_price_is_locked_after_the_first_sale(self):
		self.sell()

		with self.assertRaises(frappe.ValidationError):
			self.save_as(self.owner, [self.current_input(prices=[inr(1500)])])

	def test_sold_ticket_type_cannot_be_deleted(self):
		self.sell()

		with self.assertRaises(TicketTypeHasSales):
			self.save_as(self.owner, [])

	def test_rejects_a_ticket_type_from_another_event(self):
		other_event = create_event("Other Ticket Types Event", self.team)
		foreign = self.make_ticket_type("Foreign", event=other_event)

		with self.assertRaises(TicketTypeNotFound):
			self.save_as(self.owner, [self.current_input(), TicketTypeInput(name=foreign, title="Foreign")])


class TestTicketTypePrices(TicketTypesTestCase):
	def save_prices(self, *prices):
		return self.save_as(self.owner, [self.current_input(prices=[inr(1000), *prices])])

	def test_lists_sales_per_currency(self):
		self.save_prices(usd(15))
		self.sell("USD")

		payload = self.save_prices(usd(15))

		row = next(row for row in payload["ticket_types"] if row["name"] == self.ticket_type)
		self.assertEqual([price["tickets_sold"] for price in row["prices"]], [0, 1])

	def test_price_is_locked_after_a_sale_in_its_currency(self):
		self.save_prices(usd(15))
		self.sell("USD")

		self.save_as(self.owner, [self.current_input(prices=[inr(1200), usd(15)])])
		with self.assertRaises(frappe.ValidationError):
			self.save_prices(usd(20))
		with self.assertRaises(frappe.ValidationError):
			self.save_prices()

	def test_saves_and_removes_a_second_price(self):
		payload = self.save_prices(usd(15))

		row = next(row for row in payload["ticket_types"] if row["name"] == self.ticket_type)
		self.assertEqual(
			[(price["currency"], price["price"]) for price in row["prices"]], [("INR", 1000), ("USD", 15)]
		)

		self.save_prices()
		self.assertEqual(len(frappe.get_doc("Event Ticket Type", self.ticket_type).prices), 1)

	def test_paid_ticket_cannot_be_free_in_another_currency(self):
		with self.assertRaises(frappe.ValidationError):
			self.save_prices(usd(0))

	def test_rejects_a_currency_twice(self):
		with self.assertRaises(frappe.ValidationError):
			self.save_prices(usd(15), usd(15))


def inr(price):
	return TicketTypePriceInput(currency="INR", price=price)


def usd(price):
	return TicketTypePriceInput(currency="USD", price=price)
