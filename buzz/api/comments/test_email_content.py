from pathlib import Path

import frappe
from frappe.tests import UnitTestCase

from buzz.api.comments.activity import email_attachments
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

	def test_snippet_reads_as_one_line(self):
		self.assertEqual(
			reply("outlook_reply.html").snippet(),
			"Hello Harsh, Please find the updated abstract below. I have also attached the slides. "
			"Warm Regards, Priya Raman",
		)

	def test_only_images_in_the_message_count_as_its_own(self):
		email = EmailContent(
			'<div>See the floor plan:</div><div><img src="/private/files/plan.png?fid=1"></div>'
			'<div>Thanks,</div><div>Ravi <img src="/private/files/linkedin.png?fid=2"></div>'
			'<div><img src="/private/files/logo.png?fid=3"></div>'
		)
		self.assertEqual(email.body_image_sources(), ["/private/files/plan.png?fid=1"])

	def test_attachments_leave_out_signature_images(self):
		content = '<p>Slides attached.</p><p>Thanks,<br>Ravi</p><img src="/private/files/logo.png?fid=3">'
		files = [
			frappe._dict(file_name="slides.pdf", file_url="/private/files/slides.pdf", file_size=2_400_000),
			frappe._dict(file_name="logo.png", file_url="/private/files/logo.png", file_size=4_000),
		]
		attachments = email_attachments(files, content, EmailContent(content).body_image_sources())
		self.assertEqual([attachment.name for attachment in attachments], ["slides.pdf"])
