# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

from frappe.tests import IntegrationTestCase

from buzz.api.booking.services import create_add_on_doc
from buzz.tests.factories import (
	BuzzCustomFieldFactory,
	BuzzEventFactory,
	EventBookingFactory,
	EventTicketFactory,
	EventTicketTypeFactory,
	TicketAddOnFactory,
	UserFactory,
)
from buzz.ticketing.report.detailed_event_registrations.detailed_event_registrations import (
	execute,
	get_columns,
	get_data,
)

FIXED_COLUMNS = ("ticket_id", "attendee_name", "attendee_email", "booking_id", "ticket_type", "booking_user")


class TestDetailedEventRegistrationsReport(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.booker = UserFactory.create_once("report-booker@example.com").name
		cls.event = BuzzEventFactory.create().name
		cls.filters = {"event": cls.event}
		cls.standard_type = EventTicketTypeFactory.create(event=cls.event, title="Standard")
		cls.vip_type = EventTicketTypeFactory.create(event=cls.event, title="VIP")

	def test_execute_returns_empty_without_an_event(self):
		self.assertEqual(execute(None), ([], []))
		self.assertEqual(execute({}), ([], []))

	def test_execute_returns_columns_and_data_with_event_filter(self):
		self.create_booking()

		columns, data = execute(self.filters)

		self.assertGreater(len(columns), 0)
		self.assertGreater(len(data), 0)

	def test_get_columns_returns_fixed_columns(self):
		fieldnames = self.column_fieldnames()

		for fieldname in FIXED_COLUMNS:
			self.assertIn(fieldname, fieldnames)

	def test_get_columns_includes_enabled_custom_field_columns(self):
		self.create_custom_field("company_name")
		self.create_custom_field("disabled_field", enabled=0)

		fieldnames = self.column_fieldnames()

		self.assertIn("cf_company_name", fieldnames)
		self.assertNotIn("cf_disabled_field", fieldnames)

	def test_get_columns_includes_enabled_add_on_columns(self):
		add_on = self.create_add_on()
		disabled_add_on = TicketAddOnFactory.create(event=self.event, enabled=0)

		fieldnames = self.column_fieldnames()

		self.assertIn(f"addon_{add_on.name}", fieldnames)
		self.assertNotIn(f"addon_{disabled_add_on.name}", fieldnames)

	def test_get_columns_includes_each_utm_name_once(self):
		self.create_booking(utm_parameters=[{"utm_name": "utm_source", "value": "google"}])
		self.create_booking(
			utm_parameters=[
				{"utm_name": "utm_source", "value": "facebook"},
				{"utm_name": "utm_medium", "value": "cpc"},
			]
		)

		fieldnames = self.column_fieldnames()

		self.assertEqual(fieldnames.count("utm_utm_source"), 1)
		self.assertIn("utm_utm_medium", fieldnames)

	def test_get_data_returns_only_submitted_tickets(self):
		draft = EventTicketFactory.create(event=self.event, ticket_type=self.standard_type.name)
		submitted = self.submit_ticket()

		ticket_ids = [row["ticket_id"] for row in self.report_rows()]

		self.assertNotIn(draft.name, ticket_ids)
		self.assertIn(submitted.name, ticket_ids)

	def test_get_data_includes_correct_ticket_info(self):
		attendee = self.attendee(first_name="Test Attendee", email="testattendee@example.com")
		booking = self.create_booking(attendees=[attendee])

		row = self.row_for_booking(booking.name)

		self.assertEqual(row["attendee_name"], "Test Attendee")
		self.assertEqual(row["attendee_email"], "testattendee@example.com")
		self.assertEqual(row["ticket_type"], "Standard")
		self.assertEqual(row["booking_user"], self.booker)

	def test_get_data_includes_custom_field_values_from_ticket(self):
		self.create_custom_field("dietary_preference", applied_to="Ticket")
		ticket = self.submit_ticket(additional_fields=[additional_field("dietary_preference", "Vegetarian")])

		self.assertEqual(self.row_for_ticket(ticket.name)["cf_dietary_preference"], "Vegetarian")

	def test_get_data_custom_field_ticket_priority_over_booking(self):
		self.create_custom_field("organization", applied_to="Ticket")
		booking = EventBookingFactory.create(
			event=self.event,
			attendees=[self.attendee()],
			additional_fields=[additional_field("organization", "Booking Org")],
		)
		ticket = self.submit_ticket(
			booking=booking.name, additional_fields=[additional_field("organization", "Ticket Org")]
		)

		self.assertEqual(self.row_for_ticket(ticket.name)["cf_organization"], "Ticket Org")

	def test_get_data_falls_back_to_booking_custom_field(self):
		self.create_custom_field("company", applied_to="Booking")
		booking = self.create_booking(additional_fields=[additional_field("company", "Acme Inc")])

		self.assertEqual(self.row_for_booking(booking.name)["cf_company"], "Acme Inc")

	def test_get_data_includes_add_on_values(self):
		add_on = self.create_add_on()
		add_ons = create_add_on_doc("AddOn User", [{"add_on": add_on.name, "value": "XL"}])
		booking = self.create_booking(attendees=[self.attendee(add_ons=add_ons.name)])

		self.assertEqual(self.row_for_booking(booking.name)[f"addon_{add_on.name}"], "XL")

	def test_get_data_includes_utm_values(self):
		booking = self.create_booking(
			utm_parameters=[
				{"utm_name": "utm_source", "value": "facebook"},
				{"utm_name": "utm_campaign", "value": "summer_promo"},
			]
		)

		row = self.row_for_booking(booking.name)

		self.assertEqual((row["utm_utm_source"], row["utm_utm_campaign"]), ("facebook", "summer_promo"))

	def test_get_data_handles_multiple_tickets_per_booking(self):
		standard = self.attendee(email="one@example.com")
		vip = self.attendee(email="two@example.com", ticket_type=self.vip_type.name)
		booking = self.create_booking(attendees=[standard, vip])

		rows = {row["attendee_email"]: row for row in self.report_rows() if row["booking_id"] == booking.name}

		self.assertEqual(rows["one@example.com"]["ticket_type"], "Standard")
		self.assertEqual(rows["two@example.com"]["ticket_type"], "VIP")

	def test_report_with_no_tickets(self):
		event = BuzzEventFactory.create().name

		columns, data = execute({"event": event})

		self.assertGreater(len(columns), 0)
		self.assertEqual(data, [])

	def test_report_with_missing_booking(self):
		ticket = self.submit_ticket()

		self.assertEqual(self.row_for_ticket(ticket.name)["booking_user"], "")

	def test_report_column_ordering(self):
		self.create_custom_field("custom_col")
		add_on = self.create_add_on()
		self.create_booking(utm_parameters=[{"utm_name": "utm_test", "value": "test"}])

		fieldnames = self.column_fieldnames()
		positions = [
			fieldnames.index(fieldname)
			for fieldname in ("booking_user", "cf_custom_col", f"addon_{add_on.name}", "utm_utm_test")
		]

		self.assertEqual(positions, sorted(positions))

	def create_booking(self, attendees: list[dict] | None = None, **overrides):
		booking = EventBookingFactory.create(
			event=self.event, user=self.booker, attendees=attendees or [self.attendee()], **overrides
		)
		booking.submit()
		return booking

	def attendee(self, first_name: str = "Attendee", email: str = "attendee@example.com", **values):
		return {"ticket_type": self.standard_type.name, "first_name": first_name, "email": email, **values}

	def submit_ticket(self, **overrides):
		return EventTicketFactory.create(
			"submitted", event=self.event, ticket_type=self.standard_type.name, **overrides
		)

	def create_custom_field(self, fieldname: str, **overrides):
		return BuzzCustomFieldFactory.create(
			event=self.event, label=fieldname.replace("_", " ").title(), fieldname=fieldname, **overrides
		)

	def create_add_on(self):
		return TicketAddOnFactory.create(event=self.event, user_selects_option=1, options="S\nM\nL\nXL")

	def column_fieldnames(self) -> list[str]:
		return [column["fieldname"] for column in get_columns(self.filters)]

	def report_rows(self) -> list[dict]:
		return get_data(self.filters, get_columns(self.filters))

	def row_for_ticket(self, ticket: str) -> dict:
		return next(row for row in self.report_rows() if row["ticket_id"] == ticket)

	def row_for_booking(self, booking: str) -> dict:
		return next(row for row in self.report_rows() if row["booking_id"] == booking)


def additional_field(fieldname: str, value: str) -> dict:
	return {"fieldname": fieldname, "label": fieldname.replace("_", " ").title(), "value": value}
