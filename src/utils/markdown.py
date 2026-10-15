"""
Convert Markdown into ESC/POS printer commands.

The module is split into two parts:

* :func:`markdown_to_commands` is a pure function that turns a Markdown
  string into a list of :class:`TextCommand` / :class:`QrCommand` /
  :class:`LineBreak` objects.
* :func:`print_markdown` applies those commands to an ``escpos``-style
  printer object.

Supported syntax:

* ATX headers (``#`` through ``######``). Header levels 1-3 are printed
  larger (sizes 4, 3 and 2 respectively); every other header uses size 1.
* Bold using ``**text**`` or ``__text__``.
* Underline using ``<u>text</u>`` (double underline).
* Inline links (``[label](url)``). The label is printed as text and the
  URL is rendered as a QR code.

Styles can be combined (for example ``**<u>text</u>**``). Markers are
line-scoped and do not carry over to the next line.
"""
# pylint: disable=R0903

from dataclasses import dataclass
import re
from typing import Any, List, Union

DEFAULT_TEXT_SIZE = 1
DEFAULT_QR_SIZE = 8

# Header levels 1-3 map to larger text sizes; deeper headers stay normal.
HEADER_SIZES = {1: 4, 2: 3, 3: 2}

_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_TRAILING_HASHES_RE = re.compile(r"\s+#+\s*$")
_INLINE_RE = re.compile(
    r"(?P<bold>\*\*|__)"
    r"|(?P<underline_open><u>)"
    r"|(?P<underline_close></u>)"
    r"|(?P<link>\[(?P<label>[^\]]*)\]\((?P<url>[^)]+)\))",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TextCommand:
    """A command instructing the printer to render styled text."""

    text: str
    size: int = DEFAULT_TEXT_SIZE
    bold: bool = False
    underline: bool = False


@dataclass(frozen=True)
class QrCommand:
    """A command instructing the printer to render a QR code."""

    content: str
    size: int = DEFAULT_QR_SIZE


@dataclass(frozen=True)
class LineBreak:
    """A command instructing the printer to end the current line."""


Command = Union[TextCommand, QrCommand, LineBreak]


def _header_size(level: int) -> int:
    """
    Return the text size that should be used for a header level.

    :param level: Header level (number of leading ``#`` characters).
    :type level: int
    :return: Text size multiplier.
    :rtype: int
    """
    return HEADER_SIZES.get(level, DEFAULT_TEXT_SIZE)


def _parse_inline(line: str, qr_size: int, size: int = DEFAULT_TEXT_SIZE) -> List[Command]:
    """
    Parse a single line into styled text, QR and style-toggle commands.

    Whitespace inside the line is preserved so that styled spans stay on
    the same printed line.

    :param line: Line of Markdown to process (already stripped).
    :type line: str
    :param qr_size: Size passed to the printer's QR function.
    :type qr_size: int
    :param size: Text size multiplier for the generated text commands.
    :type size: int
    :return: Ordered list of commands for the line.
    :rtype: List[Command]
    """
    commands: List[Command] = []
    position = 0
    bold = False
    underline = False

    for match in _INLINE_RE.finditer(line):
        if match.start() > position:
            commands.append(TextCommand(
                line[position:match.start()],
                size=size,
                bold=bold,
                underline=underline,
            ))

        if match.group("bold"):
            bold = not bold
        elif match.group("underline_open"):
            underline = True
        elif match.group("underline_close"):
            underline = False
        else:
            label = match.group("label").strip()
            url = match.group("url").strip()
            if label:
                commands.append(TextCommand(label, size=size, bold=bold, underline=underline))
            commands.append(QrCommand(url, size=qr_size))

        position = match.end()

    if position < len(line):
        commands.append(TextCommand(
            line[position:],
            size=size,
            bold=bold,
            underline=underline,
        ))

    return commands


def markdown_to_commands(markdown: str, qr_size: int = DEFAULT_QR_SIZE) -> List[Command]:
    """
    Convert a Markdown string into a list of printer commands.

    :param markdown: Markdown content to convert.
    :type markdown: str
    :param qr_size: Size to use for generated QR codes.
    :type qr_size: int
    :return: Ordered list of commands describing what to print.
    :rtype: List[Command]
    """
    commands: List[Command] = []

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        header = _HEADER_RE.match(line)
        if header:
            level = len(header.group(1))
            text = _TRAILING_HASHES_RE.sub("", header.group(2)).strip()
            commands.extend(_parse_inline(text, qr_size, size=_header_size(level)))
            commands.append(LineBreak())
            continue

        commands.extend(_parse_inline(line, qr_size))
        commands.append(LineBreak())

    return commands


def print_markdown(printer: Any, markdown: str, qr_size: int = DEFAULT_QR_SIZE) -> None:
    """
    Convert Markdown and send the resulting commands to a printer.

    :param printer: An ``escpos``-style printer exposing ``set``, ``text``
        and ``qr`` methods.
    :type printer: Any
    :param markdown: Markdown content to print.
    :type markdown: str
    :param qr_size: Size to use for generated QR codes.
    :type qr_size: int
    :return: None
    :rtype: None
    """
    for command in markdown_to_commands(markdown, qr_size=qr_size):
        if isinstance(command, LineBreak):
            printer.text("\n")
        elif isinstance(command, QrCommand):
            printer.qr(command.content, size=command.size)
        else:
            printer.set(
                custom_size=True,
                width=command.size,
                height=command.size,
                bold=command.bold,
                underline=2 if command.underline else 0,
            )
            printer.text(command.text)
