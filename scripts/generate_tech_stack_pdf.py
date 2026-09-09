#!/usr/bin/env python3
"""Convert VIGIL_TECH_STACK_GUIDE.md to a formatted PDF."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from generate_handbook_pdf import HandbookPDF, build_pdf, sanitize, write_code_block, write_table, write_wrapped  # noqa: E402
import generate_handbook_pdf as handbook_mod  # noqa: E402

MD_PATH = ROOT / "docs" / "VIGIL_TECH_STACK_GUIDE.md"
PDF_PATH = ROOT / "docs" / "Vigil_Tech_Stack_Guide.pdf"
DESKTOP_COPY = Path.home() / "Desktop" / "Vigil_Tech_Stack_Guide.pdf"


def main() -> None:
    handbook_mod.PDF_PATH = PDF_PATH
    build_pdf(MD_PATH.read_text(encoding="utf-8"))
    shutil.copy2(PDF_PATH, DESKTOP_COPY)
    print(f"Desktop copy: {DESKTOP_COPY}")


if __name__ == "__main__":
    main()
