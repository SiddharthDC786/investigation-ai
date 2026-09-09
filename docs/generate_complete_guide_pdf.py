#!/usr/bin/env python3
"""Combine TEAM_HANDBOOK + tech stack rationale into one shareable PDF."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import generate_handbook_pdf as handbook_mod  # noqa: E402
from generate_handbook_pdf import build_pdf  # noqa: E402

HANDBOOK_PATH = ROOT / "docs" / "TEAM_HANDBOOK.md"
TECH_STACK_PATH = ROOT / "docs" / "VIGIL_TECH_STACK_GUIDE.md"
COMBINED_MD_PATH = ROOT / "docs" / "VIGIL_COMPLETE_GUIDE.md"
PDF_PATH = ROOT / "docs" / "Vigil_Complete_Guide.pdf"
DESKTOP_COPY = Path.home() / "Desktop" / "Vigil_Complete_Guide.pdf"

PART_B_MARKER = "## 3. Frontend Technologies"


def build_combined_markdown() -> str:
    handbook = HANDBOOK_PATH.read_text(encoding="utf-8").rstrip()
    tech = TECH_STACK_PATH.read_text(encoding="utf-8")
    idx = tech.find(PART_B_MARKER)
    if idx == -1:
        raise SystemExit(f"Could not find tech stack section marker in {TECH_STACK_PATH}")

    tech_body = tech[idx:].strip()
    part_b = f"""---

# Part B — Technology Stack: Role & Rationale

*Every technology below explains **what it does in Vigil**, **why we chose it**, and **where it appears in the project**.*

{tech_body}
"""

    combined = f"{handbook}\n\n{part_b}"
    COMBINED_MD_PATH.write_text(combined, encoding="utf-8")
    return combined


def main() -> None:
    handbook_mod.PDF_PATH = PDF_PATH
    handbook_mod.FOOTER_TEXT = "Vigil — Smart India Hackathon 2026 · Shareable documentation"
    build_pdf(build_combined_markdown())
    shutil.copy2(PDF_PATH, DESKTOP_COPY)
    print(f"Combined markdown: {COMBINED_MD_PATH}")
    print(f"Desktop copy: {DESKTOP_COPY}")


if __name__ == "__main__":
    main()
