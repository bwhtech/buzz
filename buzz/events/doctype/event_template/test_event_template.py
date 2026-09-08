# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from buzz.api.forms.test_forms import ensure_event_host
from buzz.events.doctype.buzz_event.buzz_event import create_from_template
from buzz.events.doctype.event_template.event_template import create_template_from_event


class TestEventTemplate(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.create_test_fixtures()

	@classmethod
	def create_test_fixtures(cls):
		"""Create required test data: Event Category, Host, etc."""
		# Create Event Category if not exists
		if not frappe.db.exists("Event Category", "Test Category"):
			frappe.get_doc({"doctype": "Event Category", "category_name": "Test Category"}).insert(
				ignore_permissions=True
			)

	def tearDown(self):
		"""Clean up test data after each test"""
		frappe.db.rollback()

	# ==================== Template Creation Tests ====================

	def test_create_template_basic(self):
		"""Test creating a basic Event Template"""
		template = frappe.get_doc(
			{
				"doctype": "Event Template",
				"template_name": "Test Webinar Template",
				"category": "Test Category",
				"host": ensure_event_host("Test Host"),
				"medium": "Online",
				"about": "Test description",
			}
		)
		template.insert()

		self.assertEqual(template.template_name, "Test Webinar Template")
		self.assertEqual(template.category, "Test Category")
		self.assertEqual(template.medium, "Online")

	def test_create_template_with_ticket_types(self):
		"""Test creating a template with ticket types"""
		template = frappe.get_doc(
			{
				"doctype": "Event Template",
				"template_name": "Template with Tickets",
				"category": "Test Category",
				"host": ensure_event_host("Test Host"),
				"template_ticket_types": [
					{
						"title": "Early Bird",
						"price": 100,
						"currency": "INR",
						"is_published": 1,
						"max_tickets_available": 50,
					},
					{"title": "Regular", "price": 200, "currency": "INR", "is_published": 1},
				],
			}
		)
		template.insert()

		self.assertEqual(len(template.template_ticket_types), 2)
		self.assertEqual(template.template_ticket_types[0].title, "Early Bird")
		self.assertEqual(template.template_ticket_types[0].price, 100)

	def test_create_template_with_add_ons(self):
		"""Test creating a template with add-ons"""
		template = frappe.get_doc(
			{
				"doctype": "Event Template",
				"template_name": "Template with Add-ons",
				"category": "Test Category",
				"host": ensure_event_host("Test Host"),
				"template_add_ons": [
					{"title": "T-Shirt", "price": 500, "currency": "INR", "enabled": 1},
					{
						"title": "Lunch",
						"price": 300,
						"currency": "INR",
						"user_selects_option": 1,
						"options": "Veg\nNon-Veg",
						"enabled": 1,
					},
				],
			}
		)
		template.insert()

		self.assertEqual(len(template.template_add_ons), 2)
		self.assertEqual(template.template_add_ons[1].user_selects_option, 1)

	def test_create_template_with_custom_fields(self):
		"""Test creating a template with custom fields"""
		template = frappe.get_doc(
			{
				"doctype": "Event Template",
				"template_name": "Template with Custom Fields",
				"category": "Test Category",
				"host": ensure_event_host("Test Host"),
				"template_custom_fields": [
					{
						"label": "Company Name",
						"fieldname": "company_name",
						"fieldtype": "Data",
						"applied_to": "Booking",
						"mandatory": 1,
						"enabled": 1,
					},
					{
						"label": "Dietary Preference",
						"fieldname": "dietary_preference",
						"fieldtype": "Select",
						"options": "Veg\nNon-Veg\nVegan",
						"applied_to": "Ticket",
						"enabled": 1,
					},
				],
			}
		)
		template.insert()

		self.assertEqual(len(template.template_custom_fields), 2)
		self.assertEqual(template.template_custom_fields[0].mandatory, 1)

	# ==================== Create Event from Template Tests ====================

	def test_create_event_from_template_all_options(self):
		"""Test creating an event from template with all options selected"""
		# Create template
		template = frappe.get_doc(
			{
				"doctype": "Event Template",
				"template_name": "Full Template",
				"category": "Test Category",
				"host": ensure_event_host("Test Host"),
				"medium": "Online",
				"about": "Template about text",
				"apply_tax": 1,
				"tax_label": "GST",
				"tax_percentage": 18,
				"template_ticket_types": [
					{"title": "Standard", "price": 500, "currency": "INR", "is_published": 1}
				],
				"template_add_ons": [{"title": "Workshop", "price": 1000, "currency": "INR", "enabled": 1}],
				"template_custom_fields": [
					{
						"label": "Phone",
						"fieldname": "phone",
						"fieldtype": "Phone",
						"applied_to": "Booking",
						"enabled": 1,
					}
				],
			}
		)
		template.insert()

		# Create event from template with all options
		options = {
			"category": 1,
			"host": 1,
			"medium": 1,
			"about": 1,
			"apply_tax": 1,
			"tax_label": 1,
			"tax_percentage": 1,
			"ticket_types": 1,
			"add_ons": 1,
			"custom_fields": 1,
		}

		event_name = create_from_template(template.name, frappe.as_json(options))
		event = frappe.get_doc("Buzz Event", event_name)

		# Verify event fields
		self.assertEqual(event.category, "Test Category")
		self.assertEqual(event.host, ensure_event_host("Test Host"))
		self.assertEqual(event.medium, "Online")
		self.assertEqual(event.about, "Template about text")
		self.assertEqual(event.apply_tax, 1)
		self.assertEqual(event.tax_percentage, 18)

		# Verify ticket types created (excluding default "Normal" ticket type)
		ticket_types = frappe.get_all(
			"Event Ticket Type", filters={"event": event_name, "title": "Standard"}, fields=["title", "price"]
		)
		self.assertEqual(len(ticket_types), 1)
		self.assertEqual(ticket_types[0].title, "Standard")

		# Verify add-ons created
		add_ons = frappe.get_all("Ticket Add-on", filters={"event": event_name}, fields=["title", "price"])
		self.assertEqual(len(add_ons), 1)
		self.assertEqual(add_ons[0].title, "Workshop")

		# Verify custom fields created
		custom_fields = frappe.get_all(
			"Buzz Custom Field", filters={"event": event_name}, fields=["label", "fieldtype"]
		)
		self.assertEqual(len(custom_fields), 1)
		self.assertEqual(custom_fields[0].fieldtype, "Phone")

	def test_create_event_from_template_partial_options(self):
		"""Test creating an event with only some options selected"""
		template = frappe.get_doc(
			{
				"doctype": "Event Template",
				"template_name": "Partial Template",
				"category": "Test Category",
				"host": ensure_event_host("Test Host"),
				"medium": "In Person",
				"about": "Should not be copied",
				"template_ticket_types": [
					{"title": "VIP", "price": 2000, "currency": "INR", "is_published": 1}
				],
			}
		)
		template.insert()

		# Copy category, host (required) and ticket types, but not medium/about
		options = {"category": 1, "host": 1, "medium": 0, "about": 0, "ticket_types": 1}

		event_name = create_from_template(template.name, frappe.as_json(options))
		event = frappe.get_doc("Buzz Event", event_name)

		# Category should be copied
		self.assertEqual(event.category, "Test Category")

		# Host should be copied (it's mandatory)
		self.assertEqual(event.host, ensure_event_host("Test Host"))

		# About should NOT be copied
		self.assertFalse(event.about)

		# Ticket types should be copied
		ticket_types = frappe.get_all("Event Ticket Type", filters={"event": event_name, "title": "VIP"})
		self.assertEqual(len(ticket_types), 1)

	def test_create_event_from_template_no_linked_docs(self):
		"""Test creating an event without copying linked documents"""
		template = frappe.get_doc(
			{
				"doctype": "Event Template",
				"template_name": "No Linked Docs Template",
				"category": "Test Category",
				"host": ensure_event_host("Test Host"),
				"template_ticket_types": [
					{"title": "General", "price": 100, "currency": "INR", "is_published": 1}
				],
			}
		)
		template.insert()

		# Copy fields but not linked docs
		options = {"category": 1, "host": 1, "ticket_types": 0, "add_ons": 0, "custom_fields": 0}

		event_name = create_from_template(template.name, frappe.as_json(options))

		# Event fields should be copied
		event = frappe.get_doc("Buzz Event", event_name)
		self.assertEqual(event.category, "Test Category")

		# No "General" ticket type should be created (only default "Normal")
		ticket_types = frappe.get_all("Event Ticket Type", filters={"event": event_name, "title": "General"})
		self.assertEqual(len(ticket_types), 0)

	# ==================== Save as Template Tests ====================

	def test_save_event_as_template(self):
		"""Test saving an existing event as a template"""
		# Create an event with ticket types and add-ons
		event = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": "Source Event",
				"category": "Test Category",
				"host": ensure_event_host("Test Host"),
				"start_date": frappe.utils.today(),
				"start_time": "09:00:00",
				"end_time": "18:00:00",
				"medium": "Online",
				"about": "Event description",
			}
		)
		event.insert()

		# Create ticket type for the event
		ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": event.name,
				"title": "Premium",
				"price": 1500,
				"currency": "INR",
				"is_published": 1,
			}
		)
		ticket_type.insert()

		# Create add-on for the event
		add_on = frappe.get_doc(
			{
				"doctype": "Ticket Add-on",
				"event": event.name,
				"title": "Swag Kit",
				"price": 500,
				"currency": "INR",
				"enabled": 1,
			}
		)
		add_on.insert()

		# Save as template (convert event.name to string as it's an int autoname)
		options = {"category": 1, "host": 1, "medium": 1, "about": 1, "ticket_types": 1, "add_ons": 1}

		template_name = create_template_from_event(
			str(event.name), "My Event Template", frappe.as_json(options)
		)
		template = frappe.get_doc("Event Template", template_name)

		# Verify template fields
		self.assertEqual(template.template_name, "My Event Template")
		self.assertEqual(template.category, "Test Category")
		self.assertEqual(template.medium, "Online")

		# Verify ticket types in template (excluding default "Normal")
		premium_tickets = [t for t in template.template_ticket_types if t.title == "Premium"]
		self.assertEqual(len(premium_tickets), 1)
		self.assertEqual(premium_tickets[0].price, 1500)

		# Verify add-ons in template
		self.assertEqual(len(template.template_add_ons), 1)
		self.assertEqual(template.template_add_ons[0].title, "Swag Kit")

	def test_save_event_as_template_partial(self):
		"""Test saving event as template with only some options"""
		event = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": "Partial Source Event",
				"category": "Test Category",
				"host": ensure_event_host("Test Host"),
				"start_date": frappe.utils.today(),
				"start_time": "09:00:00",
				"end_time": "18:00:00",
				"medium": "In Person",
				"about": "Should be copied",
				"apply_tax": 1,
				"tax_percentage": 18,
			}
		)
		event.insert()

		# Only save category and about (convert event.name to string as it's an int autoname)
		options = {"category": 1, "host": 0, "medium": 0, "about": 1, "apply_tax": 0}

		template_name = create_template_from_event(
			str(event.name), "Partial Template 2", frappe.as_json(options)
		)
		template = frappe.get_doc("Event Template", template_name)

		self.assertEqual(template.category, "Test Category")
		self.assertEqual(template.about, "Should be copied")
		self.assertFalse(template.host)
		self.assertFalse(template.apply_tax)

	# ==================== Round Trip Tests ====================

	def test_round_trip_event_to_template_to_event(self):
		"""Test full round trip: Event -> Template -> New Event"""
		# Step 1: Create original event
		original_event = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": "Original Conference",
				"category": "Test Category",
				"host": ensure_event_host("Test Host"),
				"start_date": frappe.utils.today(),
				"start_time": "09:00:00",
				"end_time": "18:00:00",
				"medium": "In Person",
				"about": "Annual conference description",
				"apply_tax": 1,
				"tax_label": "GST",
				"tax_percentage": 18,
			}
		)
		original_event.insert()

		# Add ticket types
		for ticket_data in [
			{"title": "Early Bird", "price": 1000},
			{"title": "Regular", "price": 1500},
			{"title": "VIP", "price": 3000},
		]:
			frappe.get_doc(
				{
					"doctype": "Event Ticket Type",
					"event": original_event.name,
					"title": ticket_data["title"],
					"price": ticket_data["price"],
					"currency": "INR",
					"is_published": 1,
				}
			).insert()

		# Step 2: Save as template (convert event.name to string as it's an int autoname)
		template_options = {
			"category": 1,
			"host": 1,
			"medium": 1,
			"about": 1,
			"apply_tax": 1,
			"tax_label": 1,
			"tax_percentage": 1,
			"ticket_types": 1,
		}
		template_name = create_template_from_event(
			str(original_event.name), "Conference Template", frappe.as_json(template_options)
		)

		# Step 3: Create new event from template
		event_options = {
			"category": 1,
			"host": 1,
			"medium": 1,
			"about": 1,
			"apply_tax": 1,
			"tax_label": 1,
			"tax_percentage": 1,
			"ticket_types": 1,
		}
		new_event_name = create_from_template(template_name, frappe.as_json(event_options))
		new_event = frappe.get_doc("Buzz Event", new_event_name)

		# Verify new event matches original
		self.assertEqual(new_event.category, original_event.category)
		self.assertEqual(new_event.host, original_event.host)
		self.assertEqual(new_event.medium, original_event.medium)
		self.assertEqual(new_event.about, original_event.about)
		self.assertEqual(new_event.tax_percentage, original_event.tax_percentage)

		# Verify ticket types match (excluding default "Normal")
		new_ticket_types = frappe.get_all(
			"Event Ticket Type",
			filters={"event": new_event_name, "title": ["in", ["Early Bird", "Regular", "VIP"]]},
			fields=["title", "price"],
			order_by="price",
		)
		self.assertEqual(len(new_ticket_types), 3)
		self.assertEqual(new_ticket_types[0].title, "Early Bird")
		self.assertEqual(new_ticket_types[0].price, 1000)

	# ==================== Edge Case Tests ====================

	def test_create_event_empty_template(self):
		"""Test creating event from template with minimal data"""
		# Template with required fields for Buzz Event (category and host are mandatory)
		template = frappe.get_doc(
			{
				"doctype": "Event Template",
				"template_name": "Empty Template",
				"category": "Test Category",
				"host": ensure_event_host("Test Host"),
			}
		)
		template.insert()

		options = {"category": 1, "host": 1}
		event_name = create_from_template(template.name, frappe.as_json(options))

		# Should create event without errors
		self.assertTrue(frappe.db.exists("Buzz Event", event_name))

	def test_template_name_required(self):
		"""Test that template_name is required"""
		template = frappe.get_doc({"doctype": "Event Template", "category": "Test Category"})

		# Template uses autoname: field:template_name, so it raises ValidationError not MandatoryError
		with self.assertRaises(frappe.exceptions.ValidationError):
			template.insert()

	def test_duplicate_template_name(self):
		"""Test handling of duplicate template names"""
		frappe.get_doc({"doctype": "Event Template", "template_name": "Duplicate Name"}).insert()

		duplicate = frappe.get_doc({"doctype": "Event Template", "template_name": "Duplicate Name"})

		with self.assertRaises(frappe.exceptions.DuplicateEntryError):
			duplicate.insert()
