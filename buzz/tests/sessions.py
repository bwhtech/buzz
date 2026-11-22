import threading
from unittest.mock import patch

import frappe
from frappe.tests.classes.context_managers import set_user

# How long the first operation waits, mid-way, for the overlapping one to finish.
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
		try:
			with set_user("Administrator"):
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


def overlap(outer: Session, owner: type, hook: str, inner: Session) -> None:
	"""Pause `outer` once at `owner.hook`, with the locks it holds by then, while `inner` runs alongside."""
	original = getattr(owner, hook)

	def run_inner_then_continue(document, *args, **kwargs):
		if threading.current_thread() is outer and not inner.is_alive() and not inner.ident:
			inner.start()
			inner.join(OVERLAP_SECONDS)
		return original(document, *args, **kwargs)

	with patch.object(owner, hook, run_inner_then_continue):
		outer.start()
		outer.join()
	inner.join()
