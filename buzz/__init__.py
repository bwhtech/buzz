__version__ = "2.0.0-beta.5"

import os

if os.environ.get("CI"):
	import frappe

	# Not toggle_test_mode: it also writes frappe.local.flags, which does not exist when bench
	# imports apps for CLI commands. frappe.init seeds local.flags.in_test from this.
	frappe.in_test = True
