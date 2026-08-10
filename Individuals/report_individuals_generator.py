import pandas as pd
import io
import os
import pymysql
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

def get_previous_period(period_str):
    """تحديد سنة وربع الفترة السابقة بدقة (مثال: الربع الثاني 2026 -> الربع الأول 2026)"""
    try:
        parts = period_str.split(" - ")
        year = int(parts[0].strip())
        q_text = parts[1].strip()
        
        quarters = ["الربع الأول", "الربع الثاني", "الربع الثالث", "الربع الرابع"]
        if q_text in quarters:
            idx = quarters.index(q_text)
            if idx > 0:
                return year, quarters[idx - 1]
            else:
                return year - 1, "الربع الرابع"
    except:
        pass
    return None, None

def fetch_specific_period_data(year_val, period_val):
    """جلب بيانات ربع معين مباشرة من قاعدة البيانات"""
    try:
        connection = pymysql.connect(
            host='localhost',
            port=3307,
            user='root',
            password='COOP@nllr2026',
            database='individuals_experience_db',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            query = """
                SELECT ind.IndicatorName, res.RatingValue AS CurrentValue
                FROM individualmeasurementrecords mr
                JOIN individualindicatorresponses res ON mr.RecordID = res.RecordID
                JOIN sharedindicators ind ON res.IndicatorID = ind.IndicatorID
                WHERE mr.Year = %s AND mr.Period = %s
            """
            cursor.execute(query, (year_val, period_val))
            rows = cursor.fetchall()
            
            factor_query = """
                SELECT f.FactorName, fr.RatingValue
                FROM individualmeasurementrecords mr
                JOIN individualfactorresponses fr ON mr.RecordID = fr.RecordID
                JOIN sharedcsatfactors f ON fr.FactorID = f.FactorID
                WHERE mr.Year = %s AND mr.Period = %s
            """
            cursor.execute(factor_query, (year_val, period_val))
            f_rows = cursor.fetchall()
        connection.close()
        return rows, f_rows
    except:
        return [], []

def calculate_metrics(rows, factors_rows):
    res_dict = {}
    
    # حساب CES (-100 إلى 100)
    ces_high = sum(1 for r in rows if "CES" in str(r.get('IndicatorName', '')).upper() and r.get('CurrentValue') is not None and float(r.get('CurrentValue', 0)) >= 4)
    ces_low = sum(1 for r in rows if "CES" in str(r.get('IndicatorName', '')).upper() and r.get('CurrentValue') is not None and float(r.get('CurrentValue', 0)) <= 2)
    ces_total = sum(1 for r in rows if "CES" in str(r.get('IndicatorName', '')).upper() and r.get('CurrentValue') is not None)
    res_dict["CES"] = ((ces_high - ces_low) / ces_total * 100) if ces_total > 0 else None
    
    # حساب NPS (-100 إلى 100)
    nps_p = sum(1 for r in rows if "NPS" in str(r.get('IndicatorName', '')).upper() and r.get('CurrentValue') is not None and float(r.get('CurrentValue', 0)) >= 9)
    nps_d = sum(1 for r in rows if "NPS" in str(r.get('IndicatorName', '')).upper() and r.get('CurrentValue') is not None and float(r.get('CurrentValue', 0)) <= 6)
    nps_total = sum(1 for r in rows if "NPS" in str(r.get('IndicatorName', '')).upper() and r.get('CurrentValue') is not None)
    res_dict["NPS"] = ((nps_p - nps_d) / nps_total * 100) if nps_total > 0 else None
    
    # حساب عوامل CSAT الـ 8 (0 إلى 100%)
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
            if csat_val < 0: csat_val = 0.0
            res_dict[f"CSAT - {fname}"] = csat_val
        else:
            res_dict[f"CSAT - {fname}"] = None
            
    return res_dict

def get_previous_period(period_str):
    """تحديد سنة وربع الفترة السابقة بدقة (مثال: الربع الأول 2026 -> الربع الرابع 2025)"""
    try:
        parts = period_str.split(" - ")
        year = int(parts[0].strip())
        q_text = parts[1].strip()
        
        quarters = ["الربع الأول", "الربع الثاني", "الربع الثالث", "الربع الرابع"]
        if q_text in quarters:
            idx = quarters.index(q_text)
            if idx > 0:
                return year, quarters[idx - 1]
            else:
                return year - 1, "الربع الرابع"
    except:
        pass
    return None, None

def build_summary_matrix(p_name, rows, factors_rows):
    summary_list = []
    
    # 1. حساب الفترة الحالية المكتوبة في التقرير
    curr_metrics = calculate_metrics(rows, factors_rows)
    
    # 2. الانتقال تلقائياً للربع الذي يسبقه (حتى لو اخترتي فترة واحدة منفردة)
    prev_year, prev_period_val = get_previous_period(p_name)
    prev_metrics = {}
    if prev_year and prev_period_val:
        p_rows, p_f_rows = fetch_specific_period_data(prev_year, prev_period_val)
        if p_rows or p_f_rows:
            prev_metrics = calculate_metrics(p_rows, p_f_rows)
            
    # CES (مع تعبئة Previous إذا وجدت بيانات الربع السابق)
    c_ces = curr_metrics.get("CES")
    p_ces = prev_metrics.get("CES")
    summary_list.append({
        "Indicator": "CES",
        "Previous": f"{p_ces:.2f}" if p_ces is not None else "-",
        "Target": "76.00",
        "Current": f"{c_ces:.2f}" if c_ces is not None else "-"
    })
    
    # NPS (مع تعبئة Previous إذا وجدت بيانات الربع السابق)
    c_nps = curr_metrics.get("NPS")
    p_nps = prev_metrics.get("NPS")
    summary_list.append({
        "Indicator": "NPS",
        "Previous": f"{p_nps:.2f}" if p_nps is not None else "-",
        "Target": "69.00",
        "Current": f"{c_nps:.2f}" if c_nps is not None else "-"
    })
    
    # CSAT Factors (مع تعبئة Previous لكل عامل إذا وجدت بيانات الربع السابق)
    for key, c_val in curr_metrics.items():
        if key.startswith("CSAT -"):
            p_val = prev_metrics.get(key)
            summary_list.append({
                "Indicator": key,
                "Previous": f"{p_val:.2f}%" if p_val is not None else "-",
                "Target": "85.00%",
                "Current": f"{c_val:.2f}%" if c_val is not None else "-"
            })
            
    return summary_list

def generate_excel(period, periods_data, factors_data):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for p_name, rows in periods_data.items():
            f_rows = factors_data.get(p_name, [])
            matrix = build_summary_matrix(p_name, rows, f_rows)
            df_period = pd.DataFrame(matrix)
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
        matrix = build_summary_matrix(p_name, rows, f_rows)
        
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