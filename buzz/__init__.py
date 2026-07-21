__version__ = "1.0.0"

import os

if os.environ.get("CI"):
	import frappe
	from frappe.tests.utils import toggle_test_mode

	toggle_test_mode(True)
