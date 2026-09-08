# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.forms.test_forms import ensure_event_host
from buzz.ticketing.report.detailed_event_registrations.detailed_event_registrations import (
	execute,
	get_add_ons_for_event,
	get_booking_additional_fields,
	get_booking_map,
	get_booking_utm_params,
	get_columns,
	get_custom_fields_for_event,
	get_data,
	get_ticket_add_ons,
	get_ticket_additional_fields,
	get_ticket_type_map,
	get_utm_params_for_event,
)


class TestDetailedEventRegistrationsReport(IntegrationTestCase):
	"""Integration tests for the Detailed Event Registrations report."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.test_event = cls._create_test_event()
		cls.test_ticket_type = cls._create_test_ticket_type(cls.test_event)
		cls.test_ticket_type_vip = cls._create_test_ticket_type(cls.test_event, title="VIP", price=500)

	@classmethod
	def _create_test_event(cls):
		"""Create a test event for the report tests."""
		# Check if test event already exists
		if frappe.db.exists("Buzz Event", {"route": "test-report-event"}):
			return frappe.get_doc("Buzz Event", {"route": "test-report-event"})

		# Create required dependencies
		if not frappe.db.exists("Event Category", "Test Category"):
			frappe.get_doc({"doctype": "Event Category", "category_name": "Test Category"}).insert()

		event = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": "Test Report Event",
				"route": "test-report-event",
				"category": "Test Category",
				"host": ensure_event_host("Test Host"),
				"start_date": frappe.utils.today(),
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"medium": "Online",
				"apply_tax": False,
			}
		).insert()
		return event

	@classmethod
	def _create_test_ticket_type(cls, event, title="Standard", price=100):
		"""Create a test ticket type."""
		return frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": event.name,
				"title": title,
				"price": price,
				"is_published": True,
			}
		).insert()

	def _create_booking_with_tickets(
		self,
		attendees_data=None,
		utm_parameters=None,
		additional_fields=None,
		submit=True,
	):
		"""Helper to create a booking with tickets."""
		if attendees_data is None:
			attendees_data = [
				{
					"first_name": "John Doe",
					"email": "john@test.com",
					"ticket_type": self.test_ticket_type.name,
				}
			]

		booking_data = {
			"doctype": "Event Booking",
			"event": self.test_event.name,
			"user": "Administrator",
			"attendees": attendees_data,
		}

		if utm_parameters:
			booking_data["utm_parameters"] = utm_parameters

		if additional_fields:
			booking_data["additional_fields"] = additional_fields

		booking = frappe.get_doc(booking_data).insert()

		if submit:
			booking.submit()

		return booking

	def _create_custom_field(self, label, fieldname, applied_to="Ticket", fieldtype="Data"):
		"""Helper to create a custom field for the event."""
		return frappe.get_doc(
			{
				"doctype": "Buzz Custom Field",
				"event": self.test_event.name,
				"label": label,
				"fieldname": fieldname,
				"fieldtype": fieldtype,
				"applied_to": applied_to,
				"enabled": 1,
				"order": 1,
			}
		).insert()

	def _create_ticket_add_on(self, title, price=50, user_selects_option=True, options="S\nM\nL\nXL"):
		"""Helper to create a ticket add-on for the event."""
		return frappe.get_doc(
			{
				"doctype": "Ticket Add-on",
				"event": self.test_event.name,
				"title": title,
				"price": price,
				"enabled": 1,
				"user_selects_option": user_selects_option,
				"options": options if user_selects_option else None,
			}
		).insert()

	def _get_ticket_for_booking(self, booking_name, attendee_email=None):
		"""Helper to get a ticket from a booking."""
		filters = {"booking": booking_name}
		if attendee_email:
			filters["attendee_email"] = attendee_email
		ticket_names = frappe.get_all("Event Ticket", filters=filters, pluck="name")
		if ticket_names:
			return frappe.get_doc("Event Ticket", ticket_names[0])
		return None

	# ==================== Test execute function ====================

	def test_execute_returns_empty_without_filters(self):
		"""Test that execute returns empty results without filters."""
		columns, data = execute(None)
		self.assertEqual(columns, [])
		self.assertEqual(data, [])

	def test_execute_returns_empty_without_event_filter(self):
		"""Test that execute returns empty results without event filter."""
		columns, data = execute({})
		self.assertEqual(columns, [])
		self.assertEqual(data, [])

	def test_execute_returns_columns_and_data_with_event_filter(self):
		"""Test that execute returns proper columns and data with event filter."""
		# Create a submitted booking
		self._create_booking_with_tickets()

		columns, data = execute({"event": self.test_event.name})

		self.assertIsInstance(columns, list)
		self.assertIsInstance(data, list)
		self.assertGreater(len(columns), 0)
		self.assertGreater(len(data), 0)

	# ==================== Test get_columns function ====================

	def test_get_columns_returns_fixed_columns(self):
		"""Test that get_columns returns the required fixed columns."""
		columns = get_columns({"event": self.test_event.name})

		fieldnames = [col["fieldname"] for col in columns]
		expected_fieldnames = [
			"ticket_id",
			"attendee_name",
			"attendee_email",
			"booking_id",
			"ticket_type",
			"booking_user",
		]

		for expected in expected_fieldnames:
			self.assertIn(expected, fieldnames)

	def test_get_columns_includes_custom_field_columns(self):
		"""Test that custom field columns are included."""
		# Create a custom field
		custom_field = self._create_custom_field("Company Name", "company_name")

		columns = get_columns({"event": self.test_event.name})
		fieldnames = [col["fieldname"] for col in columns]

		self.assertIn("cf_company_name", fieldnames)

		# Clean up
		custom_field.delete()

	def test_get_columns_includes_add_on_columns(self):
		"""Test that add-on columns are included."""
		# Create a ticket add-on
		add_on = self._create_ticket_add_on("T-Shirt Size")

		columns = get_columns({"event": self.test_event.name})
		fieldnames = [col["fieldname"] for col in columns]

		self.assertIn(f"addon_{add_on.name}", fieldnames)

		# Clean up
		add_on.delete()

	def test_get_columns_includes_utm_columns(self):
		"""Test that UTM parameter columns are included."""
		# Create a booking with UTM parameters
		self._create_booking_with_tickets(
			utm_parameters=[
				{"utm_name": "utm_source", "value": "google"},
				{"utm_name": "utm_medium", "value": "cpc"},
			]
		)

		columns = get_columns({"event": self.test_event.name})
		fieldnames = [col["fieldname"] for col in columns]

		self.assertIn("utm_utm_source", fieldnames)
		self.assertIn("utm_utm_medium", fieldnames)

	# ==================== Test get_data function ====================

	def test_get_data_returns_only_submitted_tickets(self):
		"""Test that only submitted tickets are returned."""
		# Create a draft booking (not submitted)
		self._create_booking_with_tickets(
			attendees_data=[
				{
					"first_name": "Draft User",
					"email": "draft@test.com",
					"ticket_type": self.test_ticket_type.name,
				}
			],
			submit=False,
		)

		# Create a submitted booking
		self._create_booking_with_tickets(
			attendees_data=[
				{
					"first_name": "Submitted User",
					"email": "submitted@test.com",
					"ticket_type": self.test_ticket_type.name,
				}
			],
			submit=True,
		)

		columns = get_columns({"event": self.test_event.name})
		data = get_data({"event": self.test_event.name}, columns)

		# Check that draft user is not in data
		attendee_names = [row["attendee_name"] for row in data]
		self.assertNotIn("Draft User", attendee_names)
		self.assertIn("Submitted User", attendee_names)

	def test_get_data_includes_correct_ticket_info(self):
		"""Test that ticket information is correctly included."""
		booking = self._create_booking_with_tickets(
			attendees_data=[
				{
					"first_name": "Test Attendee",
					"email": "testattendee@test.com",
					"ticket_type": self.test_ticket_type.name,
				}
			]
		)

		columns = get_columns({"event": self.test_event.name})
		data = get_data({"event": self.test_event.name}, columns)

		# Find the row for our test attendee
		test_row = next((row for row in data if row["attendee_name"] == "Test Attendee"), None)

		self.assertIsNotNone(test_row)
		self.assertEqual(test_row["attendee_email"], "testattendee@test.com")
		self.assertEqual(test_row["booking_id"], booking.name)
		# Check ticket type is the title from the ticket type we created
		self.assertEqual(test_row["ticket_type"], self.test_ticket_type.title)
		self.assertEqual(test_row["booking_user"], "Administrator")

	def test_get_data_includes_custom_field_values_from_ticket(self):
		"""Test that custom field values from tickets are included."""
		# Create a custom field
		custom_field = self._create_custom_field(
			"Dietary Preference", "dietary_preference", applied_to="Ticket"
		)

		# Create a standalone ticket with additional fields (not via booking)
		ticket = frappe.get_doc(
			{
				"doctype": "Event Ticket",
				"ticket_type": self.test_ticket_type.name,
				"attendee_name": "Dietary Test User",
				"attendee_email": "dietary@test.com",
				"additional_fields": [
					{
						"fieldname": "dietary_preference",
						"label": "Dietary Preference",
						"value": "Vegetarian",
					}
				],
			}
		).insert()
		ticket.submit()

		columns = get_columns({"event": self.test_event.name})
		data = get_data({"event": self.test_event.name}, columns)

		# Find the row for our ticket
		test_row = next((row for row in data if row["ticket_id"] == ticket.name), None)

		self.assertIsNotNone(test_row)
		self.assertEqual(test_row["cf_dietary_preference"], "Vegetarian")

		# Clean up
		custom_field.delete()

	def test_get_data_custom_field_ticket_priority_over_booking(self):
		"""Test that ticket-level custom field values take priority over booking-level."""
		# Create a custom field
		custom_field = self._create_custom_field("Organization", "organization", applied_to="Ticket")

		# Create a standalone ticket with both booking and ticket level custom fields
		# Since we can't easily add ticket-level fields after submission, we use direct insertion
		# First create the ticket with ticket-level field
		ticket = frappe.get_doc(
			{
				"doctype": "Event Ticket",
				"ticket_type": self.test_ticket_type.name,
				"attendee_name": "Priority Test User",
				"attendee_email": "priority@test.com",
				"additional_fields": [
					{
						"fieldname": "organization",
						"label": "Organization",
						"value": "Ticket Org",
					}
				],
			}
		).insert()

		# Create a booking with organization field and link the ticket
		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"attendees": [
					{
						"first_name": "Priority Test User",
						"email": "priority@test.com",
						"ticket_type": self.test_ticket_type.name,
					}
				],
				"additional_fields": [
					{
						"fieldname": "organization",
						"label": "Organization",
						"value": "Booking Org",
					}
				],
			}
		).insert()

		# Update the ticket to link to this booking
		ticket.booking = booking.name
		ticket.save()

		# Submit the ticket
		ticket.submit()

		columns = get_columns({"event": self.test_event.name})
		data = get_data({"event": self.test_event.name}, columns)

		# Find the row for our ticket
		test_row = next((row for row in data if row["ticket_id"] == ticket.name), None)

		self.assertIsNotNone(test_row)
		# Ticket value should take priority
		self.assertEqual(test_row["cf_organization"], "Ticket Org")

		# Clean up
		custom_field.delete()

	def test_get_data_falls_back_to_booking_custom_field(self):
		"""Test that booking-level custom field is used when ticket doesn't have it."""
		# Create a custom field
		custom_field = self._create_custom_field("Company", "company", applied_to="Booking")

		# Create a booking with additional fields (no ticket-level fields)
		booking = self._create_booking_with_tickets(
			additional_fields=[
				{
					"fieldname": "company",
					"label": "Company",
					"value": "Acme Inc",
				}
			]
		)

		columns = get_columns({"event": self.test_event.name})
		data = get_data({"event": self.test_event.name}, columns)

		# Find the row for our ticket
		ticket = self._get_ticket_for_booking(booking.name)
		self.assertIsNotNone(ticket, "Ticket should be created with booking")
		test_row = next((row for row in data if row["ticket_id"] == ticket.name), None)  # type: ignore

		self.assertIsNotNone(test_row)
		self.assertEqual(test_row["cf_company"], "Acme Inc")

		# Clean up
		custom_field.delete()

	def test_get_data_includes_add_on_values(self):
		"""Test that add-on values are correctly included."""
		# Create a ticket add-on
		add_on = self._create_ticket_add_on("T-Shirt Size")

		# Create attendee add-on doc
		attendee_add_on = frappe.get_doc(
			{
				"doctype": "Attendee Ticket Add-on",
				"add_ons": [{"add_on": add_on.name, "value": "XL"}],
			}
		).insert()

		# Create a booking with the add-on
		booking = self._create_booking_with_tickets(
			attendees_data=[
				{
					"first_name": "AddOn User",
					"email": "addon@test.com",
					"ticket_type": self.test_ticket_type.name,
					"add_ons": attendee_add_on.name,
				}
			]
		)

		columns = get_columns({"event": self.test_event.name})
		data = get_data({"event": self.test_event.name}, columns)

		# Find the row for our ticket
		ticket = self._get_ticket_for_booking(booking.name)
		self.assertIsNotNone(ticket, "Ticket should be created with booking")
		test_row = next((row for row in data if row["ticket_id"] == ticket.name), None)  # type: ignore

		self.assertIsNotNone(test_row)
		self.assertEqual(test_row[f"addon_{add_on.name}"], "XL")

		# Clean up
		add_on.delete()

	def test_get_data_includes_utm_values(self):
		"""Test that UTM parameter values are correctly included."""
		booking = self._create_booking_with_tickets(
			utm_parameters=[
				{"utm_name": "utm_source", "value": "facebook"},
				{"utm_name": "utm_campaign", "value": "summer_promo"},
			]
		)

		columns = get_columns({"event": self.test_event.name})
		data = get_data({"event": self.test_event.name}, columns)

		# Find the row for our ticket
		ticket = self._get_ticket_for_booking(booking.name)
		self.assertIsNotNone(ticket, "Ticket should be created with booking")
		test_row = next((row for row in data if row["ticket_id"] == ticket.name), None)  # type: ignore

		self.assertIsNotNone(test_row)
		self.assertEqual(test_row["utm_utm_source"], "facebook")
		self.assertEqual(test_row["utm_utm_campaign"], "summer_promo")

	def test_get_data_handles_multiple_tickets_per_booking(self):
		"""Test that multiple tickets per booking are handled correctly."""
		booking = self._create_booking_with_tickets(
			attendees_data=[
				{
					"first_name": "Attendee One",
					"email": "one@test.com",
					"ticket_type": self.test_ticket_type.name,
				},
				{
					"first_name": "Attendee Two",
					"email": "two@test.com",
					"ticket_type": self.test_ticket_type_vip.name,
				},
			]
		)

		columns = get_columns({"event": self.test_event.name})
		data = get_data({"event": self.test_event.name}, columns)

		# Find rows for both attendees
		attendee_names = [row["attendee_name"] for row in data]
		self.assertIn("Attendee One", attendee_names)
		self.assertIn("Attendee Two", attendee_names)

		# Check ticket types
		attendee_one_row = next((row for row in data if row["attendee_name"] == "Attendee One"), None)
		attendee_two_row = next((row for row in data if row["attendee_name"] == "Attendee Two"), None)

		self.assertIsNotNone(attendee_one_row)
		self.assertIsNotNone(attendee_two_row)
		self.assertEqual(attendee_one_row["ticket_type"], self.test_ticket_type.title)
		self.assertEqual(attendee_two_row["ticket_type"], self.test_ticket_type_vip.title)
		self.assertEqual(attendee_one_row["booking_id"], booking.name)
		self.assertEqual(attendee_two_row["booking_id"], booking.name)

	# ==================== Test helper functions ====================

	def test_get_custom_fields_for_event(self):
		"""Test get_custom_fields_for_event returns correct fields."""
		cf1 = self._create_custom_field("Field One", "field_one")
		cf2 = self._create_custom_field("Field Two", "field_two")

		# Create a disabled field that should not be returned
		cf3 = frappe.get_doc(
			{
				"doctype": "Buzz Custom Field",
				"event": self.test_event.name,
				"label": "Disabled Field",
				"fieldname": "disabled_field",
				"fieldtype": "Data",
				"applied_to": "Ticket",
				"enabled": 0,
				"order": 1,
			}
		).insert()

		result = get_custom_fields_for_event(self.test_event.name)

		fieldnames = [r.fieldname for r in result]
		self.assertIn("field_one", fieldnames)
		self.assertIn("field_two", fieldnames)
		self.assertNotIn("disabled_field", fieldnames)

		# Clean up
		cf1.delete()
		cf2.delete()
		cf3.delete()

	def test_get_add_ons_for_event(self):
		"""Test get_add_ons_for_event returns correct add-ons."""
		ao1 = self._create_ticket_add_on("Add-on One")
		ao2 = self._create_ticket_add_on("Add-on Two")

		# Create a disabled add-on
		ao3 = frappe.get_doc(
			{
				"doctype": "Ticket Add-on",
				"event": self.test_event.name,
				"title": "Disabled Add-on",
				"price": 50,
				"enabled": 0,
			}
		).insert()

		result = get_add_ons_for_event(self.test_event.name)

		titles = [r.title for r in result]
		self.assertIn("Add-on One", titles)
		self.assertIn("Add-on Two", titles)
		self.assertNotIn("Disabled Add-on", titles)

		# Clean up
		ao1.delete()
		ao2.delete()
		ao3.delete()

	def test_get_utm_params_for_event(self):
		"""Test get_utm_params_for_event returns distinct UTM names."""
		# Create bookings with different UTM params
		self._create_booking_with_tickets(
			utm_parameters=[
				{"utm_name": "utm_source", "value": "google"},
				{"utm_name": "utm_medium", "value": "cpc"},
			]
		)

		self._create_booking_with_tickets(
			attendees_data=[
				{
					"first_name": "Another User",
					"email": "another@test.com",
					"ticket_type": self.test_ticket_type.name,
				}
			],
			utm_parameters=[
				{"utm_name": "utm_source", "value": "facebook"},  # Duplicate name, different value
				{"utm_name": "utm_campaign", "value": "winter"},
			],
		)

		result = get_utm_params_for_event(self.test_event.name)

		# Should have 3 distinct UTM names
		self.assertIn("utm_source", result)
		self.assertIn("utm_medium", result)
		self.assertIn("utm_campaign", result)
		self.assertEqual(len(set(result)), len(result))  # All unique

	def test_get_ticket_type_map(self):
		"""Test get_ticket_type_map returns correct mapping."""
		result = get_ticket_type_map(self.test_event.name)

		# Keys are strings due to autoincrement ID handling
		self.assertIn(str(self.test_ticket_type.name), result)
		self.assertEqual(result[str(self.test_ticket_type.name)], "Standard")
		self.assertIn(str(self.test_ticket_type_vip.name), result)
		self.assertEqual(result[str(self.test_ticket_type_vip.name)], "VIP")

	def test_get_booking_map(self):
		"""Test get_booking_map returns correct mapping."""
		booking = self._create_booking_with_tickets()

		result = get_booking_map([booking.name])

		self.assertIn(booking.name, result)
		self.assertEqual(result[booking.name]["user"], "Administrator")

	def test_get_booking_map_empty_list(self):
		"""Test get_booking_map handles empty list."""
		result = get_booking_map([])
		self.assertEqual(result, {})

	def test_get_ticket_additional_fields(self):
		"""Test get_ticket_additional_fields returns correct data."""
		# Create a standalone ticket with additional fields
		ticket = frappe.get_doc(
			{
				"doctype": "Event Ticket",
				"ticket_type": self.test_ticket_type.name,
				"attendee_name": "Additional Fields Test",
				"attendee_email": "addfields@test.com",
				"additional_fields": [
					{
						"fieldname": "test_field",
						"label": "Test Field",
						"value": "Test Value",
					}
				],
			}
		).insert()

		result = get_ticket_additional_fields([ticket.name])

		self.assertIn(ticket.name, result)
		self.assertEqual(result[ticket.name]["test_field"], "Test Value")

	def test_get_ticket_additional_fields_empty_list(self):
		"""Test get_ticket_additional_fields handles empty list."""
		result = get_ticket_additional_fields([])
		self.assertEqual(result, {})

	def test_get_booking_additional_fields(self):
		"""Test get_booking_additional_fields returns correct data."""
		booking = self._create_booking_with_tickets(
			additional_fields=[
				{
					"fieldname": "booking_field",
					"label": "Booking Field",
					"value": "Booking Value",
				}
			]
		)

		result = get_booking_additional_fields([booking.name])

		self.assertIn(booking.name, result)
		self.assertEqual(result[booking.name]["booking_field"], "Booking Value")

	def test_get_booking_additional_fields_empty_list(self):
		"""Test get_booking_additional_fields handles empty list."""
		result = get_booking_additional_fields([])
		self.assertEqual(result, {})

	def test_get_ticket_add_ons(self):
		"""Test get_ticket_add_ons returns correct data."""
		add_on = self._create_ticket_add_on("Test Add-on")

		attendee_add_on = frappe.get_doc(
			{
				"doctype": "Attendee Ticket Add-on",
				"add_ons": [{"add_on": add_on.name, "value": "Medium"}],
			}
		).insert()

		booking = self._create_booking_with_tickets(
			attendees_data=[
				{
					"first_name": "Add-on Test",
					"email": "addontest@test.com",
					"ticket_type": self.test_ticket_type.name,
					"add_ons": attendee_add_on.name,
				}
			]
		)

		ticket = self._get_ticket_for_booking(booking.name)
		self.assertIsNotNone(ticket, "Ticket should be created with booking")
		result = get_ticket_add_ons([ticket.name])  # type: ignore

		self.assertIn(ticket.name, result)  # type: ignore
		self.assertEqual(result[ticket.name][add_on.name], "Medium")  # type: ignore

		# Clean up
		add_on.delete()

	def test_get_ticket_add_ons_empty_list(self):
		"""Test get_ticket_add_ons handles empty list."""
		result = get_ticket_add_ons([])
		self.assertEqual(result, {})

	def test_get_booking_utm_params(self):
		"""Test get_booking_utm_params returns correct data."""
		booking = self._create_booking_with_tickets(
			utm_parameters=[
				{"utm_name": "utm_source", "value": "twitter"},
				{"utm_name": "utm_medium", "value": "social"},
			]
		)

		result = get_booking_utm_params([booking.name])

		self.assertIn(booking.name, result)
		self.assertEqual(result[booking.name]["utm_source"], "twitter")
		self.assertEqual(result[booking.name]["utm_medium"], "social")

	def test_get_booking_utm_params_empty_list(self):
		"""Test get_booking_utm_params handles empty list."""
		result = get_booking_utm_params([])
		self.assertEqual(result, {})

	# ==================== Edge cases ====================

	def test_report_with_no_tickets(self):
		"""Test report handles events with no tickets."""
		# Create a new event with no tickets
		event = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": "Empty Event",
				"route": "empty-event-" + frappe.generate_hash(length=6),
				"category": "Test Category",
				"host": ensure_event_host("Test Host"),
				"start_date": frappe.utils.today(),
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"medium": "Online",
			}
		).insert()

		columns, data = execute({"event": event.name})

		self.assertIsInstance(columns, list)
		self.assertEqual(data, [])
		# Note: Not cleaning up the event as it may have linked dependencies in test DB

	def test_report_with_missing_booking(self):
		"""Test report handles tickets without booking reference gracefully."""
		# Create a standalone ticket without booking
		ticket = frappe.get_doc(
			{
				"doctype": "Event Ticket",
				"ticket_type": self.test_ticket_type.name,
				"attendee_name": "Standalone User",
				"attendee_email": "standalone@test.com",
			}
		).insert()
		ticket.submit()

		columns = get_columns({"event": self.test_event.name})
		data = get_data({"event": self.test_event.name}, columns)

		# Should include the ticket even without booking
		test_row = next((row for row in data if row["attendee_name"] == "Standalone User"), None)
		self.assertIsNotNone(test_row)
		self.assertEqual(test_row["booking_user"], "")

	def test_report_column_ordering(self):
		"""Test that columns are in the expected order."""
		# Create all types of dynamic columns
		custom_field = self._create_custom_field("Custom Col", "custom_col")
		add_on = self._create_ticket_add_on("Add-on Col")
		self._create_booking_with_tickets(utm_parameters=[{"utm_name": "utm_test", "value": "test"}])

		columns = get_columns({"event": self.test_event.name})
		fieldnames = [col["fieldname"] for col in columns]

		# Fixed columns should come first
		fixed_end_index = fieldnames.index("booking_user")

		# Custom fields should come after fixed columns
		cf_index = fieldnames.index("cf_custom_col")
		self.assertGreater(cf_index, fixed_end_index)

		# Add-ons should come after custom fields
		addon_index = fieldnames.index(f"addon_{add_on.name}")
		self.assertGreater(addon_index, cf_index)

		# UTM params should come last
		utm_index = fieldnames.index("utm_utm_test")
		self.assertGreater(utm_index, addon_index)

		# Clean up
		custom_field.delete()
		add_on.delete()
