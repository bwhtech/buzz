from pathlib import Path

from frappe.tests import UnitTestCase

from buzz.api.comments.email_content import EmailContent

FIXTURES = Path(__file__).parent / "fixtures"


def reply(name: str) -> EmailContent:
	return EmailContent((FIXTURES / name).read_text())


class TestEmailContent(UnitTestCase):
	def test_gmail_reply_keeps_only_what_was_written(self):
		email = reply("gmail_reply.html")
		body = email.body()
		self.assertIn("<b>Thursday, October 22nd at 2:30 PM IST</b>", body)
		self.assertTrue(body.endswith("<p>Thanks &amp; regards,</p>"))
		self.assertNotIn("<img", body)
		self.assertNotIn("----", body)
		self.assertNotIn("Karavan", body)
		self.assertIn("Frappe Events", email.quoted_body())

	def test_outlook_reply_drops_signature_below_the_name(self):
		email = reply("outlook_reply.html")
		self.assertTrue(email.body().endswith("<p>Warm Regards,<br><b>Priya Raman</b></p>"))
		self.assertNotIn("confidential", email.body())
		self.assertNotIn("MsoNormal", email.body())
		self.assertIn("could you share an updated abstract", email.quoted_body())

	def test_apple_mail_reply_drops_device_signature(self):
		email = reply("apple_mail_reply.html")
		self.assertEqual(email.body(), "<p>Sounds good, see you then! 👍</p>")
		self.assertIn("moved to Friday", email.quoted_body())

	def test_plain_reply_is_left_whole(self):
		email = EmailContent("<p>Yes, works for me.</p>")
		self.assertEqual(email.body(), "<p>Yes, works for me.</p>")
		self.assertEqual(email.quoted_body(), "")

	def test_plain_text_reply_keeps_its_line_breaks(self):
		body = EmailContent("Hi Harsh,\n\nStill keen.\n\nCheers,\nMeera").body()
		self.assertEqual(body, "<p>Hi Harsh,</p><p>Still keen.</p><p>Cheers,<br>Meera</p>")

	def test_scripts_and_unsafe_links_do_not_survive(self):
		body = EmailContent('<p>Hi <a href="javascript:alert(1)">x</a><script>alert(1)</script></p>').body()
		self.assertEqual(body, "<p>Hi <a>x</a></p>")
