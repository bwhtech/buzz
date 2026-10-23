from frappe.tests import UnitTestCase

from buzz.proposals import description_samples as samples
from buzz.proposals.description import DescriptionFormatter


def formatted(description: str) -> str:
	return DescriptionFormatter(description).html()


class TestDescriptionFormatter(UnitTestCase):
	def test_wall_of_text_becomes_paragraphs_and_a_numbered_list(self):
		html = formatted(samples.WALL_WITH_INLINE_NUMBERS)
		self.assertEqual(html.count("<p>"), 3)
		self.assertIn("<h4>You will leave with</h4><ol><li>A way to decide", html)
		self.assertEqual(html.count("<li>"), 3)

	def test_textarea_line_breaks_and_dashes_become_a_list(self):
		html = formatted(samples.TEXTAREA_WITH_BULLETS)
		self.assertIn("<h4>In this talk I will cover</h4><ul><li>why role permissions", html)
		self.assertTrue(html.endswith("<p>Audience: developers who ship custom apps.</p>"))

	def test_inline_bullets_become_a_list(self):
		self.assertEqual(
			formatted(samples.INLINE_BULLETS),
			"<p>Agenda</p><ul><li>Intro to Frappe UI</li><li>Building a form</li>"
			"<li>Shipping to Frappe Cloud</li></ul>",
		)

	def test_markdown_bold_is_rendered(self):
		self.assertTrue(formatted(samples.MARKDOWN_PASTE).startswith("<p><strong>Problem</strong></p>"))

	def test_description_laid_out_in_an_editor_is_kept(self):
		self.assertEqual(formatted(samples.ALREADY_FORMATTED), samples.ALREADY_FORMATTED)

	def test_text_is_escaped(self):
		self.assertEqual(formatted("<script>x</script>1 < 2"), "<p>1 &lt; 2</p>")
