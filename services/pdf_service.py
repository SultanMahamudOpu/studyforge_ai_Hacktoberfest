from pathlib import Path
from io import BytesIO
import re

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    KeepTogether,
)


def extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return "\n\n".join(pages).strip()


def split_pdf_text(text: str):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1800,
        chunk_overlap=250,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


def markdown_to_pdf(title: str, markdown: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=title,
        author="StudyForge AI",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "SFTitle",
        parent=styles["Title"],
        fontSize=22,
        leading=27,
        alignment=TA_CENTER,
        spaceAfter=14,
    )
    h1 = ParagraphStyle("SFH1", parent=styles["Heading1"], fontSize=17, leading=21, spaceBefore=10, spaceAfter=7)
    h2 = ParagraphStyle("SFH2", parent=styles["Heading2"], fontSize=14, leading=18, spaceBefore=9, spaceAfter=5)
    body = ParagraphStyle("SFBody", parent=styles["BodyText"], fontSize=10.5, leading=15, spaceAfter=6)
    bullet = ParagraphStyle("SFBullet", parent=body, leftIndent=12, firstLineIndent=-7)

    story = [Paragraph(escape_html(title), title_style)]

    lines = markdown.splitlines()
    buffer_lines = []

    def flush_paragraph():
        nonlocal buffer_lines
        if buffer_lines:
            text = " ".join(x.strip() for x in buffer_lines).strip()
            if text:
                story.append(Paragraph(format_inline(text), body))
                story.append(Spacer(1, 2))
            buffer_lines = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            continue

        if stripped.startswith("# "):
            flush_paragraph()
            story.append(Paragraph(format_inline(stripped[2:]), h1))
        elif stripped.startswith("## "):
            flush_paragraph()
            story.append(Paragraph(format_inline(stripped[3:]), h2))
        elif stripped.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(format_inline(stripped[4:]), h2))
        elif re.match(r"^[-*]\s+", stripped):
            flush_paragraph()
            item = re.sub(r"^[-*]\s+", "", stripped)
            story.append(Paragraph("• " + format_inline(item), bullet))
        elif re.match(r"^\d+\.\s+", stripped):
            flush_paragraph()
            story.append(Paragraph(format_inline(stripped), bullet))
        else:
            buffer_lines.append(stripped)

    flush_paragraph()

    doc.build(story)
    return buffer.getvalue()


def escape_html(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def format_inline(text):
    text = escape_html(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", text)
    return text
