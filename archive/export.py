"""
Chat export — convert a conversation's messages to Markdown, JSON, or PDF.

ponytail: PDF is built from Markdown via fpdf because it's already in deps
where available; otherwise we fallback to text. No heavy report lib.
Upgrade path: use ReportLab/weasyprint when richer PDF styling is needed.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
from datetime import datetime
from typing import List, Dict, Tuple


def to_markdown(title: str, messages: List[Dict[str, str]]) -> str:
    """Return a Markdown string of the conversation."""
    lines = [f"# {title}", ""]
    for m in messages:
        role = (m.get("role") or "user").capitalize()
        content = m.get("content") or ""
        lines.append(f"## {role}")
        lines.append("")
        lines.append(content)
        lines.append("")
    lines.append("")
    lines.append(f"_Exported {datetime.now().isoformat(timespec='seconds')}_")
    return "\n".join(lines)


def to_json(title: str, messages: List[Dict[str, str]]) -> str:
    return json.dumps(
        {"title": title, "messages": messages, "exported_at": datetime.now().isoformat()},
        ensure_ascii=False, indent=2,
    )


def to_pdf(title: str, messages: List[Dict[str, str]]) -> str:
    """Return a path to a generated PDF, or raise if fpdf isn't installed."""
    try:
        from fpdf import FPDF
    except ImportError:
        raise RuntimeError("fpdf not installed. pip install fpdf")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, title)
    pdf.ln(2)

    for m in messages:
        role = (m.get("role") or "user").capitalize()
        content = m.get("content") or ""
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 8, role)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 7, content)
        pdf.ln(2)

    out_dir = os.path.join(
        os.path.expanduser("~"), ".language_agnostic_chatbot", "exports"
    )
    os.makedirs(out_dir, exist_ok=True)
    safe = title.replace(" ", "_").replace("/", "_")[:40] or "chat"
    path = os.path.join(out_dir, f"{safe}.pdf")
    pdf.output(path)
    return path
