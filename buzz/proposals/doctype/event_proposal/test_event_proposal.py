# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import EventHostFactory, EventProposalFactory


class IntegrationTestEventProposal(IntegrationTestCase):
	def test_create_host_creates_and_links_event_host(self):
		company = f"Acme {frappe.generate_hash(length=6)}"
		proposal = EventProposalFactory.create(host_company=company, about_the_company="We host events.")

		host = proposal.create_host()

		self.assertEqual(proposal.host, host)
		self.assertEqual(frappe.db.get_value("Event Host", host, "host_name"), company)
		self.assertEqual(frappe.db.get_value("Event Host", host, "about"), "We host events.")

	def test_create_host_reuses_existing_host(self):
		company = f"Existing {frappe.generate_hash(length=6)}"
		existing = EventHostFactory.create(host_name=company)

		proposal = EventProposalFactory.create(host_company=company)
		proposal.create_host()

		self.assertEqual(proposal.host, existing.name)

	def test_reuse_fills_only_empty_host_fields(self):
		company = f"Empty {frappe.generate_hash(length=6)}"
		EventHostFactory.create(host_name=company)

		proposal = EventProposalFactory.create(
			host_company=company,
			host_company_logo="/files/proposal-logo.png",
			about_the_company="Proposal about.",
		)
		proposal.create_host()

		host = frappe.get_doc("Event Host", proposal.host)
		self.assertEqual(host.logo, "/files/proposal-logo.png")
		self.assertEqual(host.about, "Proposal about.")

	def test_reuse_does_not_overwrite_populated_host_fields(self):
		company = f"Populated {frappe.generate_hash(length=6)}"
		EventHostFactory.create(host_name=company, logo="/files/original-logo.png", about="Original about.")

		proposal = EventProposalFactory.create(
			host_company=company,
			host_company_logo="/files/proposal-logo.png",
			about_the_company="Proposal about.",
		)
		proposal.create_host()

		host = frappe.get_doc("Event Host", proposal.host)
		self.assertEqual(host.logo, "/files/original-logo.png")
		self.assertEqual(host.about, "Original about.")

	def test_create_host_requires_company_name(self):
		proposal = EventProposalFactory.create()
		with self.assertRaises(frappe.ValidationError):
			proposal.create_host()

	def test_create_host_throws_if_already_linked(self):
		proposal = EventProposalFactory.create(host_company=f"Acme {frappe.generate_hash(length=6)}")
		proposal.create_host()
		with self.assertRaises(frappe.ValidationError):
			proposal.create_host()

	def test_submit_auto_creates_host_from_company(self):
		company = f"Auto {frappe.generate_hash(length=6)}"
		proposal = EventProposalFactory.create("approved", host_company=company)

		proposal.submit()

		self.assertTrue(proposal.host)
		self.assertEqual(frappe.db.get_value("Event Host", proposal.host, "host_name"), company)
		self.assertEqual(proposal.status, "Event Created")

	def test_start_and_end_time_are_mandatory(self):
		with self.assertRaises(frappe.MandatoryError):
			EventProposalFactory.create(start_time=None, end_time=None)

	def test_submit_without_host_or_company_throws(self):
		proposal = EventProposalFactory.create("approved")
		with self.assertRaises(frappe.ValidationError):
			proposal.submit()

	def test_free_event_flag_carries_to_the_created_event(self):
		# get_mapped_doc matches on fieldname, so both doctypes must use the same one.
		company = f"Free {frappe.generate_hash(length=6)}"
		proposal = EventProposalFactory.create("approved", host_company=company, free_event=1)

		proposal.submit()

		event = frappe.get_doc("Buzz Event", {"proposal": proposal.name})
		self.assertEqual(event.free_event, 1)
