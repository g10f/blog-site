import json

from django.test import TestCase
from wagtail.admin.rich_text.converters.contentstate import ContentstateConverter
from wagtail.admin.rich_text import get_rich_text_editor_widget
from wagtail.models import Page

from blogsite.blog.campai_text import campai_details_html
from blogsite.blog.models import BlogIndexPage, EventPage, campai_details_body, stream_content


class CampaiDetailsTest(TestCase):
    """The details of a campai event (Markdown) become a rich text block with only what the editor knows."""

    def test_formatting_is_kept(self):
        html = campai_details_html("Ein **Vortrag** mit *Musik*\n\n- eins\n- [Anmeldung](https://example.com/a?x=1&y=2)\n")
        self.assertIn("<strong>Vortrag</strong>", html)
        self.assertIn("<em>Musik</em>", html)
        self.assertIn("<li>eins</li>", html)
        self.assertIn('<a href="https://example.com/a?x=1&amp;y=2">Anmeldung</a>', html)

    def test_html_in_the_markdown_shows_as_text(self):
        html = campai_details_html('Hallo <script>alert(1)</script> <img src=x onerror="alert(2)"> A & B')
        self.assertNotIn("<script", html)
        self.assertNotIn("<img", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn("A &amp; B", html)

    def test_links_other_than_web_and_mail_become_text(self):
        html = campai_details_html("[klick](javascript:alert(1)) und [Mail](mailto:info@example.com)")
        self.assertNotIn("javascript", html.replace("klick", ""))
        self.assertIn("klick", html)
        self.assertIn('<a href="mailto:info@example.com">Mail</a>', html)

    def test_unknown_formats_are_mapped(self):
        html = campai_details_html("# Programm\n\n`code`\n\n> Zitat\n\n![Bild](https://example.com/b.png)\n")
        self.assertIn("<h2>Programm</h2>", html)
        self.assertNotIn("<h1", html)
        self.assertNotIn("<code", html)
        self.assertNotIn("<blockquote", html)
        self.assertIn("Zitat", html)
        self.assertIn("Bild", html)
        self.assertNotIn("<img", html)

    def test_the_editor_reads_and_writes_it_unchanged(self):
        details = ("# Programm\n\nEin **Vortrag** mit *Musik*\n\n- eins\n\n- zwei\n\nDann:\n\n1. erstens\n\n---\n\n"
                   "[Anmeldung](https://example.com/a) <img src=x>\n")
        html = campai_details_html(details)
        converter = ContentstateConverter(get_rich_text_editor_widget().features)
        roundtrip = converter.to_database_format(converter.from_database_format(html))
        self.assertEqual(converter.to_database_format(converter.from_database_format(roundtrip)), roundtrip)
        for text in ("Programm</h2>", "<b>Vortrag</b>", "<i>Musik</i>", "zwei</li>", "erstens</li></ol>",
                     "<hr/>", 'href="https://example.com/a"', "&lt;img src=x&gt;"):
            self.assertIn(text, roundtrip)


class CampaiDetailsBodyTest(TestCase):
    def test_details_become_a_text_block(self):
        index = Page.get_first_root_node().add_child(instance=BlogIndexPage(title="Events", slug="events"))
        body = campai_details_body({"info": {"details": "Ein **Vortrag**"}})
        event = index.add_child(instance=EventPage(title="Event", slug="event", body=body))
        event.refresh_from_db()
        self.assertEqual([block.block_type for block in event.body], ["paragraph_block"])
        self.assertIn("<strong>Vortrag</strong>", str(event.body))
        # the stored body (with ids) and the new one (JSON) count as the same, so a sync saves no new revision
        self.assertEqual(stream_content(event.body), stream_content(body))

    def test_no_details_give_an_empty_body(self):
        self.assertEqual(json.loads(campai_details_body({"info": {}})), [])
