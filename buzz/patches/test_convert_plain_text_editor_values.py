import frappe
from frappe.tests import IntegrationTestCase

from buzz.patches.convert_plain_text_editor_values import execute, plain_text_to_html
from buzz.tests.factories import TalkProposalFactory


class TestConvertPlainTextEditorValues(IntegrationTestCase):
	def test_blank_lines_make_paragraphs_and_line_breaks_become_br(self):
		self.assertEqual(plain_text_to_html("One\nTwo\n\nThree"), "<p>One<br>Two</p><p>Three</p>")

	def test_text_is_escaped(self):
		self.assertEqual(plain_text_to_html("a < b & c"), "<p>a &lt; b &amp; c</p>")

	def test_patch_converts_plain_text_and_leaves_html_alone(self):
		plain = TalkProposalFactory.create(description="Line one\nLine two")
		html = TalkProposalFactory.create(description="<p>Already <b>HTML</b></p>")

		execute()
		execute()

		self.assertEqual(
			frappe.db.get_value("Talk Proposal", plain.name, "description"),
			"<p>Line one<br>Line two</p>",
		)
		self.assertEqual(
			frappe.db.get_value("Talk Proposal", html.name, "description"), "<p>Already <b>HTML</b></p>"
		)
