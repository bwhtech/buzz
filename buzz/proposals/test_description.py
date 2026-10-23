from frappe.tests import UnitTestCase

from buzz.proposals.description import DescriptionFormatter

# Descriptions as speakers actually submit them.
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


def formatted(description: str) -> str:
	return DescriptionFormatter(description).html()


class TestDescriptionFormatter(UnitTestCase):
	def test_wall_of_text_becomes_paragraphs_and_a_numbered_list(self):
		html = formatted(WALL_WITH_INLINE_NUMBERS)
		self.assertEqual(html.count("<p>"), 3)
		self.assertIn("<h4>You will leave with</h4><ol><li>A way to decide", html)
		self.assertEqual(html.count("<li>"), 3)

	def test_textarea_line_breaks_and_dashes_become_a_list(self):
		html = formatted(TEXTAREA_WITH_BULLETS)
		self.assertIn("<h4>In this talk I will cover</h4><ul><li>why role permissions", html)
		self.assertTrue(html.endswith("<p>Audience: developers who ship custom apps.</p>"))

	def test_inline_bullets_become_a_list(self):
		self.assertEqual(
			formatted(INLINE_BULLETS),
			"<p>Agenda</p><ul><li>Intro to Frappe UI</li><li>Building a form</li>"
			"<li>Shipping to Frappe Cloud</li></ul>",
		)

	def test_markdown_bold_is_rendered(self):
		self.assertTrue(formatted(MARKDOWN_PASTE).startswith("<p><strong>Problem</strong></p>"))

	def test_description_laid_out_in_an_editor_is_kept(self):
		self.assertEqual(formatted(ALREADY_FORMATTED), ALREADY_FORMATTED)

	def test_text_is_escaped(self):
		self.assertEqual(formatted("<script>x</script>1 < 2"), "<p>1 &lt; 2</p>")

	def test_typed_list_inside_paragraphs_still_becomes_a_list(self):
		html = formatted("<p>Line one.</p><p>In this talk:<br>- point A<br>- point B</p><p>Closing line.</p>")
		self.assertEqual(
			html,
			"<p>Line one.</p><h4>In this talk</h4><ul><li>point A</li><li>point B</li></ul>"
			"<p>Closing line.</p>",
		)
