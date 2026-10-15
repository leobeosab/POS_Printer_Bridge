"""
Tests for the Markdown to printer command conversion utility.
"""

import pytest

from utils.markdown import (
    LineBreak,
    QrCommand,
    TextCommand,
    markdown_to_commands,
    print_markdown,
)


class FakePrinter:
    """Minimal printer double that records the calls made against it."""

    def __init__(self):
        self.calls = []

    def set(self, **kwargs):
        """Record a ``set`` call."""
        self.calls.append(("set", kwargs))

    def text(self, txt):
        """Record a ``text`` call."""
        self.calls.append(("text", txt))

    def qr(self, content, size=8, **kwargs):
        """Record a ``qr`` call."""
        self.calls.append(("qr", {"content": content, "size": size}))


# ---------------------------------------------------------------------------
# markdown_to_commands: text, headers and line breaks
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("markdown", "expected_size"),
    [
        ("# Title", 4),
        ("## Title", 3),
        ("### Title", 2),
        ("#### Title", 1),
        ("##### Title", 1),
        ("###### Title", 1),
    ],
)
def test_header_levels_map_to_text_sizes(markdown, expected_size):
    """Each header level uses the documented text size."""
    assert markdown_to_commands(markdown) == [
        TextCommand("Title", size=expected_size),
        LineBreak(),
    ]


def test_plain_text_uses_default_size():
    """Regular text is emitted at size 1 and ends with a line break."""
    assert markdown_to_commands("Hello printer") == [
        TextCommand("Hello printer"),
        LineBreak(),
    ]


def test_header_closing_hashes_are_removed():
    """Trailing closing hashes are stripped from headers."""
    assert markdown_to_commands("## Title ##") == [
        TextCommand("Title", size=3),
        LineBreak(),
    ]


def test_hash_without_space_is_not_a_header():
    """``#NotAHeader`` is not valid ATX syntax and stays plain text."""
    assert markdown_to_commands("#NotAHeader") == [
        TextCommand("#NotAHeader"),
        LineBreak(),
    ]


def test_blank_lines_are_skipped():
    """Empty lines do not produce commands."""
    assert markdown_to_commands("\n\nHello\n\n") == [
        TextCommand("Hello"),
        LineBreak(),
    ]


def test_full_document_resets_size_after_header():
    """Text following a header returns to the default size."""
    markdown = "# Title\n\nNormal text\n\n### Sub heading\nMore text"
    assert markdown_to_commands(markdown) == [
        TextCommand("Title", size=4),
        LineBreak(),
        TextCommand("Normal text"),
        LineBreak(),
        TextCommand("Sub heading", size=2),
        LineBreak(),
        TextCommand("More text"),
        LineBreak(),
    ]


# ---------------------------------------------------------------------------
# markdown_to_commands: links
# ---------------------------------------------------------------------------

def test_link_generates_qr_code():
    """A link renders its label as text and its URL as a QR code."""
    assert markdown_to_commands("[Docs](https://example.com)") == [
        TextCommand("Docs"),
        QrCommand("https://example.com"),
        LineBreak(),
    ]


def test_link_with_surrounding_text():
    """Whitespace around a link is preserved on the same line."""
    assert markdown_to_commands("Visit [Docs](https://example.com) now") == [
        TextCommand("Visit "),
        TextCommand("Docs"),
        QrCommand("https://example.com"),
        TextCommand(" now"),
        LineBreak(),
    ]


def test_multiple_links_in_one_line():
    """Every link on a line produces its own QR code."""
    assert markdown_to_commands("[a](https://a.com) and [b](https://b.com)") == [
        TextCommand("a"),
        QrCommand("https://a.com"),
        TextCommand(" and "),
        TextCommand("b"),
        QrCommand("https://b.com"),
        LineBreak(),
    ]


def test_custom_qr_size():
    """The QR size can be overridden per conversion."""
    assert markdown_to_commands("[x](https://x.com)", qr_size=12) == [
        TextCommand("x"),
        QrCommand("https://x.com", size=12),
        LineBreak(),
    ]


# ---------------------------------------------------------------------------
# markdown_to_commands: bold and underline
# ---------------------------------------------------------------------------

def test_bold_with_surrounding_text():
    """``**`` toggles bold without breaking up the line."""
    assert markdown_to_commands("This is **bold** text") == [
        TextCommand("This is "),
        TextCommand("bold", bold=True),
        TextCommand(" text"),
        LineBreak(),
    ]


def test_bold_with_underscores():
    """``__`` is an alternative bold marker."""
    assert markdown_to_commands("__bold__") == [
        TextCommand("bold", bold=True),
        LineBreak(),
    ]


def test_unclosed_bold_keeps_bold_to_end_of_line():
    """An unmatched bold marker applies to the rest of the line only."""
    assert markdown_to_commands("**bold\nnormal") == [
        TextCommand("bold", bold=True),
        LineBreak(),
        TextCommand("normal"),
        LineBreak(),
    ]


def test_underline_with_surrounding_text():
    """``<u>`` toggles underline without breaking up the line."""
    assert markdown_to_commands("This is <u>underlined</u> text") == [
        TextCommand("This is "),
        TextCommand("underlined", underline=True),
        TextCommand(" text"),
        LineBreak(),
    ]


def test_underline_tags_are_case_insensitive():
    """``<U>``/``</U>`` are accepted as underline markers."""
    assert markdown_to_commands("<U>underlined</U>") == [
        TextCommand("underlined", underline=True),
        LineBreak(),
    ]


def test_bold_and_underline_combined():
    """Bold and underline can be applied to the same span."""
    assert markdown_to_commands("**<u>both</u>**") == [
        TextCommand("both", bold=True, underline=True),
        LineBreak(),
    ]


def test_styles_apply_to_header_text():
    """Inline styling inside a header keeps the header text size."""
    assert markdown_to_commands("# **Bold** title") == [
        TextCommand("Bold", size=4, bold=True),
        TextCommand(" title", size=4),
        LineBreak(),
    ]


# ---------------------------------------------------------------------------
# print_markdown
# ---------------------------------------------------------------------------

def test_print_markdown_sets_size_before_text():
    """Headers set the custom text size before printing."""
    printer = FakePrinter()
    print_markdown(printer, "# Title")
    assert printer.calls == [
        ("set", {"custom_size": True, "width": 4, "height": 4, "bold": False, "underline": 0}),
        ("text", "Title"),
        ("text", "\n"),
    ]


def test_print_markdown_sets_bold():
    """Bold spans enable and disable bold on the printer."""
    printer = FakePrinter()
    print_markdown(printer, "**bold**")
    assert printer.calls == [
        ("set", {"custom_size": True, "width": 1, "height": 1, "bold": True, "underline": 0}),
        ("text", "bold"),
        ("text", "\n"),
    ]


def test_print_markdown_sets_double_underline():
    """Underline spans enable and disable double underline on the printer."""
    printer = FakePrinter()
    print_markdown(printer, "<u>underlined</u>")
    assert printer.calls == [
        ("set", {"custom_size": True, "width": 1, "height": 1, "bold": False, "underline": 2}),
        ("text", "underlined"),
        ("text", "\n"),
    ]


def test_print_markdown_link_uses_qr():
    """Links are rendered through the printer's ``qr`` method."""
    printer = FakePrinter()
    print_markdown(printer, "[Docs](https://example.com)")
    assert printer.calls == [
        ("set", {"custom_size": True, "width": 1, "height": 1, "bold": False, "underline": 0}),
        ("text", "Docs"),
        ("qr", {"content": "https://example.com", "size": 8}),
        ("text", "\n"),
    ]


def test_print_markdown_forwards_custom_qr_size():
    """A custom QR size is passed through to the printer."""
    printer = FakePrinter()
    print_markdown(printer, "[Docs](https://example.com)", qr_size=10)
    assert ("qr", {"content": "https://example.com", "size": 10}) in printer.calls


def test_print_markdown_with_real_dummy_printer():
    """Integration check against the real python-escpos Dummy printer."""
    escpos_printer = pytest.importorskip("escpos.printer")
    printer = escpos_printer.Dummy()
    print_markdown(printer, "# Title\n**bold** and <u>underlined</u>\n[link](https://example.com)")
    assert b"Title" in printer.output
    assert b"bold" in printer.output
    assert b"underlined" in printer.output
