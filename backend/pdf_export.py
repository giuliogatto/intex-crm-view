from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _cell_paragraph(text, style):
    return Paragraph(escape(str(text)), style)


def build_pdf(title, headers, rows, col_widths=None):
    buffer = BytesIO()
    use_landscape = len(headers) > 6
    page_size = landscape(A4) if use_landscape else A4

    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(title, styles['Title']),
        Spacer(1, 12),
    ]

    header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=9,
        wordWrap='CJK',
    )

    table_data = [[_cell_paragraph(h, header_style) for h in headers]]
    for row in rows:
        table_data.append([_cell_paragraph(cell, cell_style) for cell in row])

    col_count = len(headers)
    available_width = page_size[0] - 30 * mm
    if col_widths is None:
        resolved_col_widths = [available_width / col_count] * col_count
    else:
        total_weight = sum(col_widths)
        resolved_col_widths = [available_width * (w / total_weight) for w in col_widths]

    table = Table(table_data, colWidths=resolved_col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    return buffer.getvalue()
