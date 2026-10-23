# Descriptions as speakers actually submit them, for tests and local seeding.
WALL_WITH_INLINE_NUMBERS = (
	"What happens when the wrong SIM card ships with the wrong device, and the person receiving it lives alone? "
	"This talk walks through an ERPNext v16 implementation for a medical devices company in India, where every smart "
	"watch, medication dispenser and gateway is tracked by IMEI and SIM ICCID, and customers order and pay on a website "
	"built outside ERPNext. We will cover the pattern, not the product: how far standard ERPNext took us (Serial No, "
	"Subscription, CRM, SLA settings, ERPNext Support), the one custom rule we added at Delivery Note to block mismatched "
	"devices before dispatch, and how website orders and online payments reach ERPNext through APIs while ERPNext stays "
	"the single source of truth. We will also look at automatic device subscriptions, post-sales support run per serial "
	"number with SLA tiers and escalation, and how the project was tested end to end over nine weeks. You will leave "
	"with: 1. A way to decide what stays native in ERPNext and what deserves custom code 2. A rule of thumb for choosing "
	"where a business rule should be enforced 3. A pattern for connecting an external website and payment gateway while "
	"keeping ERPNext as the source of truth"
)
TEXTAREA_WITH_BULLETS = (
	"Most Frappe apps outgrow their first permission model.\n\n"
	"In this talk I will cover:\n- why role permissions stop scaling\n- how we moved to query conditions\n"
	"- the tests that kept us honest\n\nAudience: developers who ship custom apps."
)
INLINE_BULLETS = "Agenda • Intro to Frappe UI • Building a form • Shipping to Frappe Cloud"
MARKDOWN_PASTE = "**Problem**\nInvoices were created twice.\n\n**Fix**\nAn idempotency key on the API."
ALREADY_FORMATTED = "<p>A walkthrough of the problem.</p><ul><li>One</li><li>Two</li></ul>"
