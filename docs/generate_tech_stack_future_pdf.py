#!/usr/bin/env python3
"""Convert VIGIL_TECH_STACK_AND_FUTURE.md to a shareable PDF."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import generate_handbook_pdf as handbook_mod  # noqa: E402
from generate_handbook_pdf import build_pdf  # noqa: E402

MD_PATH = ROOT / "docs" / "VIGIL_TECH_STACK_AND_FUTURE.md"
PDF_PATH = ROOT / "docs" / "Vigil_Tech_Stack_And_Future.pdf"
DESKTOP_COPY = Path.home() / "Desktop" / "Vigil_Tech_Stack_And_Future.pdf"


def main() -> None:
    handbook_mod.PDF_PATH = PDF_PATH
    handbook_mod.FOOTER_TEXT = "Vigil — Smart India Hackathon 2026 · Shareable documentation"
    build_pdf(MD_PATH.read_text(encoding="utf-8"))
    shutil.copy2(PDF_PATH, DESKTOP_COPY)
    print(f"Desktop copy: {DESKTOP_COPY}")


if __name__ == "__main__":
    main()
