#!/usr/bin/env python3
"""Convert TEAM_HANDBOOK.md to a formatted PDF."""

from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent
MD_PATH = ROOT / "docs" / "TEAM_HANDBOOK.md"
PDF_PATH = ROOT / "docs" / "Vigil_Team_Handbook.pdf"


class HandbookPDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, sanitize("Vigil - Smart India Hackathon PS 26189"), align="L")
        self.cell(0, 8, f"Page {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, sanitize("Confidential - Team documentation only"), align="C")


def sanitize(text: str) -> str:
    text = text.replace("\u2014", "-").replace("\u2013", "-")
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2192", "->").replace("\u2190", "<-")
    text = text.replace("\u2265", ">=").replace("\u00b7", "-")
    return text.encode("latin-1", errors="replace").decode("latin-1")


def write_wrapped(pdf: HandbookPDF, text: str, size: int = 10, style: str = "", indent: int = 0):
    pdf.set_font("Helvetica", style, size)
    pdf.set_text_color(30, 30, 30)
    pdf.set_x(pdf.l_margin + indent)
    pdf.multi_cell(0, size * 0.45 + 2, sanitize(text))


def write_code_block(pdf: HandbookPDF, lines: list[str]):
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font("Courier", "", 8)
    pdf.set_text_color(40, 40, 40)
    block = "\n".join(lines)
    if pdf.get_y() > 250:
        pdf.add_page()
    x = pdf.l_margin
    w = pdf.w - pdf.l_margin - pdf.r_margin
    h = max(6, len(lines) * 4.5 + 4)
    pdf.rect(x, pdf.get_y(), w, h, style="F")
    pdf.set_xy(x + 2, pdf.get_y() + 2)
    pdf.multi_cell(w - 4, 4.5, sanitize(block))
    pdf.ln(3)


def write_table(pdf: HandbookPDF, rows: list[list[str]]):
    if not rows:
        return
    col_count = max(len(r) for r in rows)
    page_w = pdf.w - pdf.l_margin - pdf.r_margin
    col_w = page_w / col_count

    if pdf.get_y() > 240:
        pdf.add_page()

    for i, row in enumerate(rows):
        while len(row) < col_count:
            row.append("")
        if i == 0:
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(230, 235, 240)
        else:
            pdf.set_font("Helvetica", "", 8)
            pdf.set_fill_color(252, 252, 252)
        pdf.set_text_color(30, 30, 30)
        y0 = pdf.get_y()
        x0 = pdf.l_margin
        max_h = 6
        cell_heights = []
        for cell in row:
            lines = pdf.multi_cell(col_w, 4.5, sanitize(cell), split_only=True)
            cell_heights.append(max(6, len(lines) * 4.5 + 2))
        row_h = max(cell_heights)
        if y0 + row_h > 280:
            pdf.add_page()
            y0 = pdf.get_y()
        for j, cell in enumerate(row):
            pdf.set_xy(x0 + j * col_w, y0)
            pdf.rect(x0 + j * col_w, y0, col_w, row_h, style="FD")
            pdf.set_xy(x0 + j * col_w + 1.5, y0 + 1.5)
            pdf.multi_cell(col_w - 3, 4.5, sanitize(cell))
        pdf.set_y(y0 + row_h)
    pdf.ln(3)


def parse_table_lines(lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in lines:
        if re.match(r"^\|[-| :]+\|$", line.strip()):
            continue
        if "|" in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows.append(cells)
    return rows


def build_pdf(md_text: str) -> None:
    pdf = HandbookPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    lines = md_text.splitlines()
    i = 0
    in_code = False
    code_lines: list[str] = []
    table_lines: list[str] = []
    in_table = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                write_code_block(pdf, code_lines)
                code_lines = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        if stripped.startswith("|") and "|" in stripped[1:]:
            if not in_table:
                in_table = True
                table_lines = []
            table_lines.append(stripped)
            i += 1
            continue
        elif in_table:
            write_table(pdf, parse_table_lines(table_lines))
            table_lines = []
            in_table = False

        if stripped == "---":
            pdf.ln(2)
            pdf.set_draw_color(200, 200, 200)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(4)
            i += 1
            continue

        if stripped.startswith("# "):
            if pdf.get_y() > 40:
                pdf.add_page()
            pdf.set_text_color(20, 40, 80)
            write_wrapped(pdf, stripped[2:], size=20, style="B")
            pdf.ln(4)
            i += 1
            continue

        if stripped.startswith("## "):
            if pdf.get_y() > 250:
                pdf.add_page()
            pdf.set_text_color(30, 60, 100)
            write_wrapped(pdf, stripped[3:], size=14, style="B")
            pdf.ln(2)
            i += 1
            continue

        if stripped.startswith("### "):
            pdf.set_text_color(40, 70, 110)
            write_wrapped(pdf, stripped[4:], size=11, style="B")
            pdf.ln(1)
            i += 1
            continue

        if stripped.startswith("> "):
            pdf.set_text_color(50, 50, 50)
            write_wrapped(pdf, stripped[2:], size=10, style="I", indent=4)
            pdf.ln(1)
            i += 1
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            write_wrapped(pdf, f"  •  {stripped[2:]}", size=10)
            i += 1
            continue

        m = re.match(r"^(\d+)\.\s+(.*)", stripped)
        if m:
            write_wrapped(pdf, f"  {m.group(1)}. {m.group(2)}", size=10)
            i += 1
            continue

        if stripped.startswith("**") and stripped.endswith("**"):
            write_wrapped(pdf, stripped.strip("*"), size=10, style="B")
            i += 1
            continue

        if not stripped:
            pdf.ln(2)
            i += 1
            continue

        clean = re.sub(r"\*\*(.+?)\*\*", r"\1", stripped)
        clean = re.sub(r"`(.+?)`", r"\1", clean)
        write_wrapped(pdf, clean, size=10)
        i += 1

    if in_table and table_lines:
        write_table(pdf, parse_table_lines(table_lines))
    if in_code and code_lines:
        write_code_block(pdf, code_lines)

    pdf.output(str(PDF_PATH))
    print(f"PDF written to: {PDF_PATH}")
    print(f"Size: {PDF_PATH.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    build_pdf(MD_PATH.read_text(encoding="utf-8"))
