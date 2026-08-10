import pandas as pd
import io
import os
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl import load_workbook

def process_arabic_text(text):
    reshaped_text = arabic_reshaper.reshape(str(text))
    bidi_text = get_display(reshaped_text)
    return bidi_text

def format_val(val, is_csat=False):
    if val is None or val == "None" or val == "" or str(val) == "-":
        return "-"
    try:
        num = float(val)
        formatted = f"{num:.2f}"
        return f"{formatted}%" if is_csat else formatted
    except:
        return str(val)

def build_summary_matrix(rows, factors_rows):
    summary_list = []
    
    # 1. حساب مؤشر CES النهائي بالبوينت (من -100 إلى 100)
    # المعادلة: مجموع إجابات (4 و 5) ناقص مجموع إجابات (1 و 2)
    ces_high = sum(1 for r in rows if "CES" in str(r.get('IndicatorName', '')).upper() and r.get('CurrentValue') is not None and float(r.get('CurrentValue', 0)) >= 4)
    ces_low = sum(1 for r in rows if "CES" in str(r.get('IndicatorName', '')).upper() and r.get('CurrentValue') is not None and float(r.get('CurrentValue', 0)) <= 2)
    ces_total = sum(1 for r in rows if "CES" in str(r.get('IndicatorName', '')).upper() and r.get('CurrentValue') is not None)
    
    final_ces = ((ces_high - ces_low) / ces_total * 100) if ces_total > 0 else 0.0
    
    # 2. حساب مؤشر NPS النهائي بالبوينت (من -100 إلى 100)
    # المعادلة: مجموع إجابات (9 و 10) ناقص مجموع إجابات من (0 إلى 6)
    nps_promoters = sum(1 for r in rows if "NPS" in str(r.get('IndicatorName', '')).upper() and r.get('CurrentValue') is not None and float(r.get('CurrentValue', 0)) >= 9)
    nps_detractors = sum(1 for r in rows if "NPS" in str(r.get('IndicatorName', '')).upper() and r.get('CurrentValue') is not None and float(r.get('CurrentValue', 0)) <= 6)
    nps_total = sum(1 for r in rows if "NPS" in str(r.get('IndicatorName', '')).upper() and r.get('CurrentValue') is not None)
    
    final_nps = ((nps_promoters - nps_detractors) / nps_total * 100) if nps_total > 0 else 0.0
    
    summary_list.append({
        "Indicator": "CES",
        "Previous": "-",
        "Target": "76.00",
        "Current": f"{final_ces:.2f}"
    })
    
    summary_list.append({
        "Indicator": "NPS",
        "Previous": "-",
        "Target": "69.00",
        "Current": f"{final_nps:.2f}"
    })
    
    # 3. حساب عوامل CSAT الـ 8 كنسبة مئوية (من 0 إلى 100)
    # المعادلة: مجموع إجابات (4 و 5) ناقص مجموع إجابات (1 و 2) كنسبة من الإجمالي
    factors_dict = {}
    for f in factors_rows:
        fname = f.get('FactorName', 'عامل')
        fval = f.get('RatingValue', 0)
        try:
            fval_num = float(fval)
        except:
            fval_num = 0.0
        if fname not in factors_dict:
            factors_dict[fname] = []
        factors_dict[fname].append(fval_num)
        
    for fname, vals in factors_dict.items():
        if vals:
            pos = sum(1 for v in vals if v >= 4)
            neg = sum(1 for v in vals if v <= 2)
            total = len(vals)
            
            csat_val = ((pos - neg) / total * 100) if total > 0 else 0.0
            if csat_val < 0:
                csat_val = 0.0
        else:
            csat_val = 0.0
            
        summary_list.append({
            "Indicator": f"CSAT - {fname}",
            "Previous": "-",
            "Target": "85.00%",
            "Current": f"{csat_val:.2f}%"
        })
        
    return summary_list

def generate_excel(period, periods_data, factors_data):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for p_name, rows in periods_data.items():
            f_rows = factors_data.get(p_name, [])
            matrix = build_summary_matrix(rows, f_rows)
            df_period = pd.DataFrame(matrix)
            # إعادة ترتيب الأعمدة لتطابق الطلب
            df_period = df_period[["Indicator", "Previous", "Target", "Current"]]
            safe_sheet_name = p_name.replace(" & ", "_")
            df_period.to_excel(writer, index=False, sheet_name=safe_sheet_name)

    buffer.seek(0)
    wb = load_workbook(buffer)
    
    header_fill = PatternFill(start_color="7A7F94", end_color="7A7F94", fill_type="solid")
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    alignment_center = Alignment(horizontal="center", vertical="center")

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        for col_num in range(1, ws.max_column + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = alignment_center

    final_buffer = io.BytesIO()
    wb.save(final_buffer)
    
    return final_buffer.getvalue(), f"Summary_Report_{period.replace(' ', '_')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

def generate_pdf(period, periods_data, factors_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=(842, 595), rightMargin=40, leftMargin=40, topMargin=90, bottomMargin=30)
    elements = []
    
    font_path = "C:\\Windows\\Fonts\\arial.ttf"
    font_name = "Helvetica" 
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('ArabicFont', font_path))
        font_name = 'ArabicFont'
        
    styles = getSampleStyleSheet()
    
    def add_header_footer(canvas_obj, document):
        canvas_obj.saveState()
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            canvas_obj.drawImage(logo_path, 40, 525, width=120, height=45, preserveAspectRatio=True, mask='auto')
        
        canvas_obj.setFont(font_name, 12)
        canvas_obj.drawRightString(800, 545, process_arabic_text(f"ملخص مؤشرات تجربة العميل (الأفراد) - الفترة: {period}"))
        
        canvas_obj.setLineWidth(1)
        canvas_obj.setStrokeColor(colors.HexColor('#1e253c'))
        canvas_obj.line(40, 515, 800, 515)
        canvas_obj.restoreState()

    elements.append(Spacer(1, 10))

    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=12,
        alignment=2,
        textColor=colors.HexColor('#7b5ab8'),
        spaceAfter=10,
        spaceBefore=10,
        keepWithNext=True
    )

    headers = [
        process_arabic_text("Current Value"), 
        process_arabic_text("Target Value"), 
        process_arabic_text("Previous Value"), 
        process_arabic_text("Indicator / Factor Name")
    ]
    col_widths = [120, 120, 120, 382]

    for p_name, rows in periods_data.items():
        f_rows = factors_data.get(p_name, [])
        matrix = build_summary_matrix(rows, f_rows)
        
        period_table_data = [headers]
        for item in matrix:
            row = [
                str(item["Current"]), 
                str(item["Target"]), 
                str(item["Previous"]), 
                str(item["Indicator"])
            ]
            period_table_data.append([process_arabic_text(cell) for cell in row])

        t_period = Table(period_table_data, colWidths=col_widths)
        t_period.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5a3e8d")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f4f6f9")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        period_block = KeepTogether([
            Paragraph(process_arabic_text(f"ملخص المؤشرات والعوامل للفترة: {p_name}"), section_title_style),
            t_period
        ])
        elements.append(period_block)

    doc.build(elements, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    
    return buffer.getvalue(), f"Summary_Report_{period.replace(' ', '_')}.pdf", "application/pdf"