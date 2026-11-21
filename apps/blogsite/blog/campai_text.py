"""
The details of a campai event (Markdown) as the HTML of a rich text block.

The result holds only what the rich text editor of Wagtail knows (paragraphs, headings 2 to 4, bold, italic,
lists, links, line breaks, horizontal lines). The editor converts the HTML into its own form when a page is
opened and back when it is saved; anything it doesn't know would get lost there. And the page renders this HTML
as it is, so it must not contain anything that runs in the browser.

- HTML written into the Markdown is escaped first, so it shows as text (no <script>, no <img onerror=...>, no
  unclosed tags that the editor can't read).
- Markdown that the editor doesn't know is mapped to what it knows: heading 1 to heading 2, headings 5 and 6 to
  heading 4, code to plain text, a quote to its paragraphs, an image to its alt text.
- Links keep only http, https and mailto addresses; any other link becomes its text.
"""
import html
from html.parser import HTMLParser

import markdown

ALLOWED_TAGS = {"p", "h2", "h3", "h4", "strong", "em", "ul", "ol", "li", "a", "br", "hr"}
RENAMED_TAGS = {"h1": "h2", "h5": "h4", "h6": "h4", "b": "strong", "i": "em", "pre": "p"}
VOID_TAGS = {"br", "hr"}
LINK_SCHEMES = ("http://", "https://", "mailto:")


def campai_details_html(details):
    escaped = html.escape(details, quote=False)
    cleaner = RichTextCleaner()
    cleaner.feed(markdown.markdown(escaped))
    cleaner.close()
    return "".join(cleaner.parts)


class RichTextCleaner(HTMLParser):
    """Rebuilds the HTML from the tags of ALLOWED_TAGS only; the text of other tags is kept."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.open_tags = []  # the tag written for each open start tag, or None if it was left out
        self.list_items = 0  # paragraphs inside a list item are left out, the editor doesn't have them

    def handle_starttag(self, tag, attrs):
        tag = RENAMED_TAGS.get(tag, tag)
        if tag == "img":
            alt = dict(attrs).get("alt")
            if alt:
                self.parts.append(html.escape(alt))
            return
        written = None
        if tag == "a":
            href = (dict(attrs).get("href") or "").strip()
            if href.lower().startswith(LINK_SCHEMES):
                self.parts.append(f'<a href="{html.escape(href)}">')
                written = "a"
        elif tag == "p" and self.list_items:
            written = None
        elif tag in ALLOWED_TAGS:
            self.parts.append(f"<{tag}>" if tag not in VOID_TAGS else f"<{tag}/>")
            written = None if tag in VOID_TAGS else tag
        if tag == "li":
            self.list_items += 1
        if tag not in VOID_TAGS:
            self.open_tags.append(written)

    def handle_endtag(self, tag):
        tag = RENAMED_TAGS.get(tag, tag)
        if tag in VOID_TAGS or tag == "img" or not self.open_tags:
            return
        written = self.open_tags.pop()
        if tag == "li":
            self.list_items -= 1
        if written:
            self.parts.append(f"</{written}>")

    def handle_data(self, data):
        self.parts.append(html.escape(data, quote=False))
