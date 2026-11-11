from pathlib import Path
from datetime import datetime
from html import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    LongTable,
    TableStyle,
)


FONT_NAME = "SchoolUnicode"
_FONT_REGISTERED = False


def _get_font():
    """
    Find a Unicode font when available.

    DejaVu Sans and Noto fonts are common on Ubuntu.
    Helvetica is the fallback.
    """
    global _FONT_REGISTERED

    if _FONT_REGISTERED:
        return FONT_NAME

    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansKhmer-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansKhmer-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        str(Path.home() / ".fonts/DejaVuSans.ttf"),
    ]

    for candidate in candidates:
        font_path = Path(candidate)

        if not font_path.is_file():
            continue

        try:
            pdfmetrics.registerFont(
                TTFont(FONT_NAME, str(font_path))
            )
            _FONT_REGISTERED = True
            return FONT_NAME
        except Exception:
            continue

    return "Helvetica"


def _format_amount(value, currency):
    amount = int(value)

    if currency == "USD":
        return f"${amount // 100:,}.{amount % 100:02d}"

    if currency == "KHR":
        return f"KHR {amount:,}"

    return f"{currency} {amount:,}"


def _display_value(key, value, row):
    if value is None:
        return "-"

    if key.endswith("_minor"):
        currency = row.get("currency", "")

        if currency:
            return _format_amount(value, currency)

        return str(value)

    if isinstance(value, (dict, list, tuple)):
        return str(value)

    if key in {
        "fee_type",
        "entry_type",
        "employee_type",
        "status",
        "payment_status",
        "payment_method",
    }:
        return str(value).replace("_", " ").title()

    return str(value)


def _page_footer(canvas, document):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)

    canvas.drawRightString(
        document.pagesize[0] - 15 * mm,
        10 * mm,
        f"Page {document.page}",
    )

    canvas.restoreState()


def export_text_pdf(file_path, title, text):
    """
    Export a text-based receipt or salary slip to a paginated PDF.
    Long lines are wrapped automatically.
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    font_name = _get_font()
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocumentTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#172033"),
        spaceAfter=12,
    )

    body_style = ParagraphStyle(
        "DocumentBody",
        parent=styles["Code"],
        fontName=font_name,
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#172033"),
        splitLongWords=True,
        spaceAfter=1,
    )

    story = [
        Paragraph(escape(title), title_style),
        Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            ParagraphStyle(
                "GeneratedDate",
                parent=body_style,
                alignment=TA_CENTER,
                textColor=colors.grey,
            ),
        ),
        Spacer(1, 8),
    ]

    for line in str(text).splitlines():
        safe_line = line.replace("៛", "KHR ")

        if not safe_line.strip():
            story.append(Spacer(1, 5))
        else:
            story.append(
                Paragraph(
                    escape(safe_line).replace(" ", "&nbsp;"),
                    body_style,
                )
            )

    document = SimpleDocTemplate(
        str(file_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=title,
        author="School Management System",
    )

    document.build(
        story,
        onFirstPage=_page_footer,
        onLaterPages=_page_footer,
    )

    return file_path


def export_table_pdf(file_path, title, rows):
    """
    Export report dictionaries to a paginated landscape PDF.
    Currency values are formatted from their integer minor units.
    """
    if not rows:
        raise ValueError("There is no report data to export.")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    font_name = _get_font()
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=15,
        leading=19,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#172033"),
        spaceAfter=5,
    )

    header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=7.5,
        leading=9,
        textColor=colors.white,
    )

    cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#172033"),
        splitLongWords=True,
    )

    columns = list(rows[0].keys())

    table_data = [[
        Paragraph(
            escape(
                column.replace("_minor", "").replace("_", " ").title()
            ),
            header_style,
        )
        for column in columns
    ]]

    for row in rows:
        table_data.append([
            Paragraph(
                escape(_display_value(column, row.get(column), row)),
                cell_style,
            )
            for column in columns
        ])

    page_width, _ = landscape(A4)

    document = SimpleDocTemplate(
        str(file_path),
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=16 * mm,
        bottomMargin=17 * mm,
        title=title,
        author="School Management System",
    )

    usable_width = page_width - document.leftMargin - document.rightMargin
    column_width = usable_width / len(columns)

    table = LongTable(
        table_data,
        colWidths=[column_width] * len(columns),
        repeatRows=1,
        splitByRow=1,
        hAlign="LEFT",
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#F1F5F9"),
        ]),
    ]))

    story = [
        Paragraph(escape(title), title_style),
        Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            ParagraphStyle(
                "ReportDate",
                parent=cell_style,
                alignment=TA_CENTER,
                textColor=colors.grey,
            ),
        ),
        Spacer(1, 10),
        table,
    ]

    document.build(
        story,
        onFirstPage=_page_footer,
        onLaterPages=_page_footer,
    )

    return file_path
