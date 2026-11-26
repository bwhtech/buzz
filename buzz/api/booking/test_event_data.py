import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.api.booking.cache import EventBookingCache
from buzz.api.booking.event_data import (
	build_event_booking_data,
	get_offline_methods,
	load_available_ticket_type_rows,
	ticket_type_dict_row,
)
from buzz.api.events.ticket_types import TicketTypeAccess
from buzz.tasks import unpublish_ticket_types_after_last_date
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzFormFactory,
	EventTicketCategoryFactory,
	EventTicketFactory,
	EventTicketTypeFactory,
	OfflinePaymentMethodFactory,
	TicketAddOnFactory,
	TicketHoldFactory,
)


class TestTicketTypeRow(IntegrationTestCase):
	def test_a_sales_count_and_internal_fields_do_not_reach_the_booking_page(self):
		event = BuzzEventFactory.create()
		EventTicketTypeFactory.create(
			event=event.name,
			max_tickets_available=10,
			prices=[{"currency": "INR", "price": 500}],
		)

		rows, remaining_by_type, waitlisted = load_available_ticket_type_rows(event)
		row = ticket_type_dict_row(
			rows[0],
			adds_guests_directly=False,
			remaining=remaining_by_type[str(rows[0].name)],
			waitlisted=str(rows[0].name) in waitlisted,
			event_requires_approval=bool(event.requires_approval),
		)

		self.assertNotIn("tickets_sold", row)
		self.assertNotIn("_comments", row)
		self.assertNotIn("_assign", row)
		self.assertNotIn("_liked_by", row)
		self.assertNotIn("_user_tags", row)
		self.assertNotIn("tickets_sold", row["prices"][0])
		self.assertEqual(row.max_tickets_available, 10)
		self.assertEqual(row.prices[0].price, 500)

	def test_offline_payment_method_returns_its_custom_fields(self):
		event = BuzzEventFactory.create(is_published=1)
		method = OfflinePaymentMethodFactory.create(event=event.name, enabled=1)
		custom_field = frappe.get_doc(
			{
				"doctype": "Buzz Custom Field",
				"event": event.name,
				"applied_to": "Offline Payment Form",
				"offline_payment_method": str(method.name),
				"label": "UTR Number",
				"fieldname": "utr_number",
				"fieldtype": "Data",
				"enabled": 1,
			}
		).insert(ignore_permissions=True)

		methods = get_offline_methods(event.name)

		self.assertEqual(len(methods), 1)
		self.assertEqual(len(methods[0]["custom_fields"]), 1)
		self.assertEqual(methods[0]["custom_fields"][0].name, custom_field.name)

		response = build_event_booking_data(event.route)
		self.assertEqual(len(response.offline_methods[0]["custom_fields"]), 1)


class TestEventBookingCacheInvalidation(IntegrationTestCase):
	def _warm_cache(self, event):
		# Simulate post-commit steady state so reads populate Redis.
		EventBookingCache._flush_transaction_state()
		data = build_event_booking_data(event.route)
		self.assertIsNotNone(frappe.cache.get_value(EventBookingCache.metadata_key(event.name)))
		self.assertEqual(
			frappe.cache.get_value(EventBookingCache.route_key(event.route)),
			str(event.name),
		)
		return data

	def test_warm_cache_serves_metadata_without_reloading_static_tables(self):
		event = BuzzEventFactory.create(is_published=1)
		EventTicketTypeFactory.create(event=event.name, max_tickets_available=0)
		self._warm_cache(event)

		frappe.set_user("Guest")
		try:
			with self.assertQueryCount(0):
				data = build_event_booking_data(event.route)
		finally:
			frappe.set_user("Administrator")
		self.assertTrue(data.available_ticket_types)

	def test_ticket_type_update_and_delete_invalidate_cache(self):
		event = BuzzEventFactory.create(is_published=1)
		ticket_type = EventTicketTypeFactory.create(
			event=event.name,
			title="Early Bird",
			prices=[{"currency": "INR", "price": 500}],
		)
		self._warm_cache(event)

		ticket_type.title = "Super Early Bird"
		ticket_type.prices[0].price = 750
		ticket_type.save(ignore_permissions=True)

		self.assertIsNone(frappe.cache.get_value(EventBookingCache.metadata_key(event.name)))
		refreshed = build_event_booking_data(event.route)
		matched = [row for row in refreshed.available_ticket_types if str(row.name) == str(ticket_type.name)]
		self.assertEqual(matched[0].title, "Super Early Bird")
		self.assertEqual(matched[0].prices[0].price, 750)

		self._warm_cache(event)
		ticket_type.delete(ignore_permissions=True)
		self.assertIsNone(frappe.cache.get_value(EventBookingCache.metadata_key(event.name)))
		after_delete = build_event_booking_data(event.route)
		self.assertNotIn(
			str(ticket_type.name), [str(row.name) for row in after_delete.available_ticket_types]
		)

	def test_category_add_on_offline_method_and_custom_field_invalidate_cache(self):
		event = BuzzEventFactory.create(is_published=1)
		category = EventTicketCategoryFactory.create(event=event.name, title="General", sort_order=1)
		EventTicketTypeFactory.create(event=event.name, category=category.name)
		add_on = TicketAddOnFactory.create(event=event.name, title="T-Shirt", enabled=1)
		method = OfflinePaymentMethodFactory.create(event=event.name, title="Bank Transfer", enabled=1)
		self._warm_cache(event)

		category.title = "Main Track"
		category.save(ignore_permissions=True)
		self.assertIsNone(frappe.cache.get_value(EventBookingCache.metadata_key(event.name)))
		self.assertEqual(build_event_booking_data(event.route).ticket_categories[0]["title"], "Main Track")

		self._warm_cache(event)
		add_on.title = "Hoodie"
		add_on.save(ignore_permissions=True)
		self.assertIsNone(frappe.cache.get_value(EventBookingCache.metadata_key(event.name)))
		self.assertEqual(build_event_booking_data(event.route).available_add_ons[0].title, "Hoodie")

		self._warm_cache(event)
		method.title = "NEFT Transfer"
		method.save(ignore_permissions=True)
		self.assertIsNone(frappe.cache.get_value(EventBookingCache.metadata_key(event.name)))
		self.assertEqual(build_event_booking_data(event.route).offline_methods[0]["title"], "NEFT Transfer")

		self._warm_cache(event)
		custom_field = frappe.get_doc(
			{
				"doctype": "Buzz Custom Field",
				"event": event.name,
				"applied_to": "Offline Payment Form",
				"offline_payment_method": str(method.name),
				"label": "Reference ID",
				"fieldname": "reference_id",
				"fieldtype": "Data",
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
		self.assertIsNone(frappe.cache.get_value(EventBookingCache.metadata_key(event.name)))
		self.assertEqual(
			build_event_booking_data(event.route).offline_methods[0]["custom_fields"][0].name,
			custom_field.name,
		)

	def test_registration_form_changes_invalidate_cache(self):
		event = BuzzEventFactory.create(is_published=1)
		BuzzFormFactory.set_registration_cutoff(event.name, None)
		self._warm_cache(event)

		form_name = frappe.db.get_value("Buzz Form", {"event": event.name, "form_doctype": "Event Booking"})
		form = frappe.get_doc("Buzz Form", form_name)
		form.append(
			"questions",
			{"fieldname": "org_name", "label": "Organisation", "fieldtype": "Data", "enabled": 1},
		)
		form.save(ignore_permissions=True)

		self.assertIsNone(frappe.cache.get_value(EventBookingCache.metadata_key(event.name)))
		refreshed = build_event_booking_data(event.route)
		self.assertIn("org_name", [field["fieldname"] for field in refreshed.custom_fields])

	def test_event_route_change_invalidates_old_and_new_route(self):
		event = BuzzEventFactory.create(is_published=1)
		old_route = event.route
		self._warm_cache(event)

		new_route = f"{old_route}-renamed"
		event.route = new_route
		event.save(ignore_permissions=True)

		self.assertIsNone(frappe.cache.get_value(EventBookingCache.route_key(old_route)))
		with self.assertRaises(frappe.DoesNotExistError):
			build_event_booking_data(old_route)
		self.assertEqual(build_event_booking_data(new_route).event_details["name"], event.name)

	def test_direct_db_mutations_invalidate_cache(self):
		event = BuzzEventFactory.create(is_published=1)
		expiring = EventTicketTypeFactory.create(
			event=event.name,
			is_published=1,
			auto_unpublish_after=add_days(today(), -1),
		)
		self._warm_cache(event)

		unpublish_ticket_types_after_last_date()
		self.assertIsNone(frappe.cache.get_value(EventBookingCache.metadata_key(event.name)))
		after_task = build_event_booking_data(event.route)
		self.assertNotIn(str(expiring.name), [str(row.name) for row in after_task.available_ticket_types])

		active = EventTicketTypeFactory.create(event=event.name, is_published=1, requires_approval=0)
		self._warm_cache(event)
		TicketTypeAccess(str(active.name)).update(requires_approval=True, enable_waitlist=False)
		self.assertIsNone(frappe.cache.get_value(EventBookingCache.metadata_key(event.name)))
		after_access = build_event_booking_data(event.route)
		matched = [row for row in after_access.available_ticket_types if str(row.name) == str(active.name)]
		self.assertTrue(matched[0].requires_approval)

	def test_live_capacity_stays_fresh_on_warm_cache_hit(self):
		event = BuzzEventFactory.create(is_published=1)
		ticket_type = EventTicketTypeFactory.create(event=event.name, max_tickets_available=5)
		first = self._warm_cache(event)
		matched = [row for row in first.available_ticket_types if str(row.name) == str(ticket_type.name)]
		self.assertEqual(matched[0].remaining_tickets, 5)

		EventTicketFactory.create("submitted", event=event.name, ticket_type=ticket_type.name)
		TicketHoldFactory.create(ticket_type=ticket_type.name, quantity=2)

		second = build_event_booking_data(event.route)
		matched = [row for row in second.available_ticket_types if str(row.name) == str(ticket_type.name)]
		self.assertEqual(matched[0].remaining_tickets, 2)

	def test_uncommitted_write_never_pollutes_redis_and_flush_clears_stale_entries(self):
		event = BuzzEventFactory.create(is_published=1)
		ticket_type = EventTicketTypeFactory.create(event=event.name, title="Original Title")
		self._warm_cache(event)

		ticket_type.title = "Uncommitted Title"
		ticket_type.save(ignore_permissions=True)
		# Reading inside the same uncommitted transaction sees the uncommitted change,
		# while keeping Redis unpolluted so concurrent workers never read dirty state.
		in_tx = build_event_booking_data(event.route)
		matched = [row for row in in_tx.available_ticket_types if str(row.name) == str(ticket_type.name)]
		self.assertEqual(matched[0].title, "Uncommitted Title")
		self.assertIsNone(frappe.cache.get_value(EventBookingCache.metadata_key(event.name)))

		# Even if a concurrent reader repopulated Redis before commit, commit flush clears it.
		frappe.cache.set_value(EventBookingCache.metadata_key(event.name), {"stale": True})
		EventBookingCache._flush_transaction_state()
		self.assertIsNone(frappe.cache.get_value(EventBookingCache.metadata_key(event.name)))
