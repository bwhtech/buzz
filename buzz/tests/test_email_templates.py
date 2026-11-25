import re
from pathlib import Path

from frappe.tests import UnitTestCase

EMAIL_TEMPLATES = Path(__file__).parent.parent / "templates" / "emails"

# Styles that spam filters (Rspamd MANY_INVISIBLE_PARTS) treat as hidden text.
HIDDEN_STYLE_PATTERNS = (
	r"display\s*:\s*none",
	r"visibility\s*:\s*hidden",
	r"opacity\s*:\s*0(\.0\d*)?\s*(;|$)",
	r"max-(height|width)\s*:\s*0\s*(px)?\s*(;|$)",
	r"text-indent\s*:\s*-",
	r"font-size\s*:\s*[0-2](px)?\s*(;|$)",
	r"clip\s*:",
)


class TestEmailTemplatesHaveNoHiddenText(UnitTestCase):
	def test_no_template_uses_a_hiding_style(self):
		for template in sorted(EMAIL_TEMPLATES.glob("*.html")):
			for style in re.findall(r'style="([^"]*)"', template.read_text()):
				with self.subTest(template=template.name, style=style):
					self.assertFalse(self.is_hidden(style))

	def test_detects_the_old_preheader_style(self):
		self.assertTrue(
			self.is_hidden("display:none;overflow:hidden;line-height:1px;opacity:0;max-height:0;max-width:0")
		)

	@staticmethod
	def is_hidden(style: str) -> bool:
		return any(re.search(pattern, style, re.IGNORECASE) for pattern in HIDDEN_STYLE_PATTERNS)
