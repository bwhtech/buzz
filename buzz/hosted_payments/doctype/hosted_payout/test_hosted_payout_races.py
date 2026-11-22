import threading
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.hosted_payments.doctype.hosted_payout.hosted_payout import HostedPayout
from buzz.tests.factories import BuzzTeamFactory, HostedPaymentFactory, HostedPayoutFactory

# How long the first payout operation waits, mid-way, for the overlapping one to finish.
OVERLAP_SECONDS = 3


class Session(threading.Thread):
	"""A request of its own, on another thread and database connection. It commits when it succeeds."""

	def __init__(self, action):
		super().__init__()
		self.site, self.sites_path = frappe.local.site, frappe.local.sites_path
		self.action, self.result, self.error = action, None, None

	def run(self):
		frappe.init(self.site, sites_path=self.sites_path)
		frappe.connect()
		frappe.set_user("Administrator")
		try:
			self.result = self.action()
			# A request of its own ends in a commit, as a real one does.
			frappe.db.commit()  # nosemgrep: frappe-manual-commit
		except Exception as error:
			frappe.db.rollback()
			self.error = error
		finally:
			frappe.destroy()


def in_session(action):
	session = Session(action)
	session.start()
	session.join()
	if session.error:
		raise session.error
	return session.result


def overlap(outer: Session, hook: str, inner: Session) -> None:
	"""Pause `outer` at `hook`, after Frappe has locked its payout, while `inner` runs alongside."""
	original = getattr(HostedPayout, hook)

	def run_inner_then_continue(payout):
		if threading.current_thread() is outer:
			inner.start()
			inner.join(OVERLAP_SECONDS)
		original(payout)

	with patch.object(HostedPayout, hook, run_inner_then_continue):
		outer.start()
		outer.join()
	inner.join()


def set_fallback_rate(rate: float | None) -> float | None:
	previous = frappe.db.get_single_value("Buzz Settings", "hosted_payment_fallback_rate")
	frappe.db.set_single_value("Buzz Settings", "hosted_payment_fallback_rate", rate)
	return previous


def submit(payout: str, transfer_reference: str):
	doc = frappe.get_doc("Hosted Payout", payout)
	doc.transfer_reference = transfer_reference
	doc.submit()


def cancel(payout: str):
	frappe.get_doc("Hosted Payout", payout).cancel()


class TestOverlappingPayouts(IntegrationTestCase):
	"""A payment settled by one payout and refunded after it, so two draft payouts carry the refund forward.

	Every write is committed from sessions of their own, as concurrent requests make them.
	"""

	def setUp(self):
		self.fallback_rate = in_session(lambda: set_fallback_rate(5))
		self.addCleanup(in_session, lambda: set_fallback_rate(self.fallback_rate))
		self.team, self.order_id, self.settled_by, self.drafts = in_session(self.settle_then_refund)
		self.addCleanup(in_session, self.delete_fixtures)

	def settle_then_refund(self):
		team = BuzzTeamFactory.create_owned_by().name
		order_id = HostedPaymentFactory.create("paid", team=team, amount=1000).name
		settled_by = self.drafted_payout(team)
		settled_by.transfer_reference = "UTR-SETTLE"
		settled_by.submit()
		frappe.db.set_value(
			"Hosted Payment", order_id, {"refunded_amount": 300, "status": "Partially Refunded"}
		)
		return team, order_id, settled_by.name, [self.drafted_payout(team).name for _ in range(2)]

	def drafted_payout(self, team: str):
		payout = HostedPayoutFactory.create(team=team)
		payout.get_payments()
		return payout.save()

	def delete_fixtures(self):
		payouts = frappe.get_all("Hosted Payout", {"team": self.team}, pluck="name")
		frappe.db.delete("Hosted Payout Line", {"parent": ["in", payouts]})
		frappe.db.delete("Hosted Payout", {"team": self.team})
		frappe.db.delete("Hosted Payment", {"team": self.team})
		frappe.db.delete("Buzz Team Membership", {"team": self.team})
		frappe.db.delete("Buzz Team Settings", {"name": self.team})
		frappe.db.delete("Buzz Team", {"name": self.team})

	def assert_refund_deducted_once_by(self, payout: str):
		def read():
			draft = HostedPayoutFactory.build(team=self.team)
			draft.get_payments()
			docstatus = [
				frappe.db.get_value("Hosted Payout", name, "docstatus") for name in (self.settled_by, payout)
			]
			return docstatus, frappe.db.get_value("Hosted Payment", self.order_id, "payout"), draft.lines

		docstatus, settled_by, outstanding_lines = in_session(read)
		self.assertEqual(docstatus, [1, 1])
		self.assertEqual(settled_by, self.settled_by)
		self.assertEqual(outstanding_lines, [])

	def assert_refused_without_a_deadlock(self, session: Session, message: str):
		self.assertNotIsInstance(session.error, frappe.QueryDeadlockError)
		self.assertIsInstance(session.error, frappe.ValidationError)
		self.assertIn(message, str(session.error))

	def test_cancel_overlapping_a_submit_that_deducts_its_refund_is_refused(self):
		cancelling = Session(lambda: cancel(self.settled_by))
		submitting = Session(lambda: submit(self.drafts[0], "UTR-REFUND"))

		overlap(cancelling, "before_cancel", submitting)

		self.assertIsNone(submitting.error)
		self.assert_refused_without_a_deadlock(cancelling, "Cancel it first")
		self.assert_refund_deducted_once_by(self.drafts[0])

	def test_submit_overlapping_a_cancel_of_the_settling_payout_goes_first(self):
		submitting = Session(lambda: submit(self.drafts[0], "UTR-REFUND"))
		cancelling = Session(lambda: cancel(self.settled_by))

		overlap(submitting, "on_submit", cancelling)

		self.assertIsNone(submitting.error)
		self.assert_refused_without_a_deadlock(cancelling, "Cancel it first")
		self.assert_refund_deducted_once_by(self.drafts[0])

	def test_refund_deducted_by_a_payout_submitted_meanwhile_is_not_deducted_again(self):
		late = Session(lambda: submit(self.drafts[1], "UTR-LATE"))
		first = Session(lambda: submit(self.drafts[0], "UTR-FIRST"))

		overlap(late, "before_submit", first)

		self.assertIsNone(first.error)
		self.assert_refused_without_a_deadlock(late, "Get payments again")
		self.assert_refund_deducted_once_by(self.drafts[0])
