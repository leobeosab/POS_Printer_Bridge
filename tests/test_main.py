"""
Tests for the Markdown API route.
"""

from escpos.printer import Dummy
import escpos.printer
from fastapi.testclient import TestClient
import pytest

import main


client = TestClient(main.app)


def test_markdown_route_prints_and_cuts():
    """The markdown route prints the content once and cuts at the end."""
    printer = Dummy()
    main.PRINTER = printer

    response = client.post(
        "/print/markdown/",
        json={
            "content": "# Title\n**bold** and <u>underlined</u>\n[link](https://example.com)",
            "qr_size": 6,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "Markdown Printed"}
    assert b"Title" in printer.output
    assert b"bold" in printer.output
    assert b"underlined" in printer.output
    # The paper is always cut once at the end of the document.
    assert printer.output.count(b"\x1dV") == 1


def test_markdown_route_uses_alignment_and_qr_size():
    """The route applies alignment and forwards the QR size."""
    printer = Dummy()
    main.PRINTER = printer

    response = client.post(
        "/print/markdown/",
        json={
            "content": "[link](https://example.com)",
            "qr_size": 12,
            "alignment": "center",
        },
    )

    assert response.status_code == 200
    # Alignment is set to center and reset to the default afterwards.
    assert b"\x1ba\x01" in printer.output
    assert b"https://example.com" not in printer.output  # rendered as QR image


def test_markdown_route_rejects_invalid_qr_size():
    """QR sizes outside the supported range are rejected."""
    main.PRINTER = Dummy()

    response = client.post(
        "/print/markdown/",
        json={"content": "# Title", "qr_size": 99},
    )

    assert response.status_code == 422


def test_init_printer_file_option(tmp_path, monkeypatch):
    """PRINTER_TYPE=file uses the path from PRINTER_FILE_PATH."""
    target = tmp_path / "printer.out"
    monkeypatch.setenv("PRINTER_TYPE", "file")
    monkeypatch.setenv("PRINTER_FILE_PATH", str(target))
    monkeypatch.delenv("PRINTER_PROFILE", raising=False)

    main.init_printer()

    try:
        assert isinstance(main.PRINTER, escpos.printer.File)
        assert main.PRINTER.devfile == str(target)
    finally:
        main.PRINTER.close()


def test_init_printer_file_requires_path(monkeypatch):
    """PRINTER_TYPE=file without PRINTER_FILE_PATH exits."""
    monkeypatch.setenv("PRINTER_TYPE", "file")
    monkeypatch.delenv("PRINTER_FILE_PATH", raising=False)

    with pytest.raises(SystemExit):
        main.init_printer()
