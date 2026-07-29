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
    try:
        num = float(val)
        formatted = f"{num:.2f}"
        return f"{formatted}%" if is_csat else formatted
    except:
        return str(val)

def build_service_matrix(rows):
    services_dict = {}
    for row in rows:
        dept = row['DepartmentName']
        s = row['ServiceName']
        ind = row['IndicatorName']
        p = row['PrevValue']
        t = row['TargetValue']
        c = row['CurrentValue']
        
        key = (dept, s)
        if key not in services_dict:
            services_dict[key] = {
                "Department": dept,
                "Service": s,
                "Prvious CSAT": "-", "Target CSAT": "-", "Current CSAT": "-",
                "Prvious CES": "-", "Target CES": "-", "Current CES": "-",
                "Prvious NPS": "-", "Target NPS": "-", "Current NPS": "-"
            }
        
        ind_clean = str(ind).strip().upper()
        if "CSAT" in ind_clean:
            services_dict[key]["Prvious CSAT"] = format_val(p, is_csat=True)
            services_dict[key]["Target CSAT"] = format_val(t, is_csat=True)
            services_dict[key]["Current CSAT"] = format_val(c, is_csat=True)
        elif "CES" in ind_clean:
            services_dict[key]["Prvious CES"] = format_val(p, is_csat=False)
            services_dict[key]["Target CES"] = format_val(t, is_csat=False)
            services_dict[key]["Current CES"] = format_val(c, is_csat=False)
        elif "NPS" in ind_clean:
            services_dict[key]["Prvious NPS"] = format_val(p, is_csat=False)
            services_dict[key]["Target NPS"] = format_val(t, is_csat=False)
            services_dict[key]["Current NPS"] = format_val(c, is_csat=False)
            
    return list(services_dict.values())

def generate_excel(period, periods_data):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        selected_periods_list = list(periods_data.items())
        
        # 1. شيت الملخص السنوي المجمع (Average)
        if len(selected_periods_list) > 1:
            combined_unique = {}
            for p_name, rows in periods_data.items():
                for row in rows:
                    dept = row['DepartmentName']
                    s = row['ServiceName']
                    ind = row['IndicatorName']
                    p, t, c = row['PrevValue'], row['TargetValue'], row['CurrentValue']
                    
                    key = (dept, s)
                    if key not in combined_unique:
                        combined_unique[key] = {
                            "CSAT_p": [], "CSAT_t": [], "CSAT_c": [],
                            "CES_p": [], "CES_t": [], "CES_c": [],
                            "NPS_p": [], "NPS_t": [], "NPS_c": []
                        }
                    
                    ind_clean = str(ind).strip().upper()
                    try:
                        val_p, val_t, val_c = float(p), float(t), float(c)
                    except:
                        continue

                    if "CSAT" in ind_clean:
                        combined_unique[key]["CSAT_p"].append(val_p)
                        combined_unique[key]["CSAT_t"].append(val_t)
                        combined_unique[key]["CSAT_c"].append(val_c)
                    elif "CES" in ind_clean:
                        combined_unique[key]["CES_p"].append(val_p)
                        combined_unique[key]["CES_t"].append(val_t)
                        combined_unique[key]["CES_c"].append(val_c)
                    elif "NPS" in ind_clean:
                        combined_unique[key]["NPS_p"].append(val_p)
                        combined_unique[key]["NPS_t"].append(val_t)
                        combined_unique[key]["NPS_c"].append(val_c)

            annual_rows = []
            for (dept, s), vals in combined_unique.items():
                def avg(lst, is_c=False):
                    if not lst:
                        return "-"
                    return format_val(sum(lst)/len(lst), is_csat=is_c)
                
                annual_rows.append({
                    "Department": dept,
                    "Service": s,
                    "Prvious CSAT": avg(vals["CSAT_p"], True), "Target CSAT": avg(vals["CSAT_t"], True), "Current CSAT": avg(vals["CSAT_c"], True),
                    "Prvious CES": avg(vals["CES_p"], False), "Target CES": avg(vals["CES_t"], False), "Current CES": avg(vals["CES_c"], False),
                    "Prvious NPS": avg(vals["NPS_p"], False), "Target NPS": avg(vals["NPS_t"], False), "Current NPS": avg(vals["NPS_c"], False)
                })
            
            df_annual = pd.DataFrame(annual_rows)
            df_annual.to_excel(writer, index=False, sheet_name='ملخص السنة')

        # 2. الشيتات المنفصلة لكل فترة
        for p_name, rows in periods_data.items():
            matrix = build_service_matrix(rows)
            df_period = pd.DataFrame(matrix)
            safe_sheet_name = p_name.replace(" & ", "_")
            df_period.to_excel(writer, index=False, sheet_name=safe_sheet_name)

    # إعادة فتح الملف عبر openpyxl لتلوين الصف الأول وتنسيقه في جميع الشيتات
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
    
    return final_buffer.getvalue(), f"Report_{period.replace(' ', '_')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

def generate_pdf(period, periods_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=(842, 595), rightMargin=30, leftMargin=30, topMargin=85, bottomMargin=30)
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
            canvas_obj.drawImage(logo_path, 40, 525, width=130, height=50, preserveAspectRatio=True, mask='auto')
        
        canvas_obj.setFont(font_name, 13)
        canvas_obj.drawRightString(800, 550, process_arabic_text(f"منصة تجربة العميل - التقرير الشامل للفترات: {period}"))
        
        canvas_obj.setLineWidth(1)
        canvas_obj.setStrokeColor(colors.HexColor('#1e253c'))
        canvas_obj.line(40, 515, 800, 515)
        canvas_obj.restoreState()

    elements.append(Spacer(1, 10))

    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=11,
        alignment=2,
        textColor=colors.HexColor('#7b5ab8'),
        spaceAfter=8,
        spaceBefore=15,
        keepWithNext=True
    )

    headers = [
        process_arabic_text("Current NPS"), process_arabic_text("Target NPS"), process_arabic_text("Prvious NPS"),
        process_arabic_text("Current CES"), process_arabic_text("Target CES"), process_arabic_text("Prvious CES"),
        process_arabic_text("Current CSAT"), process_arabic_text("Target CSAT"), process_arabic_text("Prvious CSAT"),
        process_arabic_text("Service"), process_arabic_text("Department")
    ]
    col_widths = [65, 65, 65, 65, 65, 65, 65, 65, 65, 90, 90]

    selected_periods_list = list(periods_data.keys())

    if len(selected_periods_list) > 1:
        combined_unique = {}
        for p_name, rows in periods_data.items():
            for row in rows:
                dept = row['DepartmentName']
                s = row['ServiceName']
                ind = row['IndicatorName']
                p, t, c = row['PrevValue'], row['TargetValue'], row['CurrentValue']
                
                key = (dept, s)
                if key not in combined_unique:
                    combined_unique[key] = {"CSAT_p": [], "CSAT_t": [], "CSAT_c": [], "CES_p": [], "CES_t": [], "CES_c": [], "NPS_p": [], "NPS_t": [], "NPS_c": []}
                
                ind_clean = str(ind).strip().upper()
                try:
                    val_p, val_t, val_c = float(p), float(t), float(c)
                except:
                    continue

                if "CSAT" in ind_clean:
                    combined_unique[key]["CSAT_p"].append(val_p)
                    combined_unique[key]["CSAT_t"].append(val_t)
                    combined_unique[key]["CSAT_c"].append(val_c)
                elif "CES" in ind_clean:
                    combined_unique[key]["CES_p"].append(val_p)
                    combined_unique[key]["CES_t"].append(val_t)
                    combined_unique[key]["CES_c"].append(val_c)
                elif "NPS" in ind_clean:
                    combined_unique[key]["NPS_p"].append(val_p)
                    combined_unique[key]["NPS_t"].append(val_t)
                    combined_unique[key]["NPS_c"].append(val_c)

        annual_table_data = [headers]
        for (dept, s), vals in combined_unique.items():
            def avg(lst, is_c=False):
                if not lst:
                    return "-"
                return format_val(sum(lst)/len(lst), is_csat=is_c)
            
            row = [
                avg(vals["NPS_c"], False), avg(vals["NPS_t"], False), avg(vals["NPS_p"], False),
                avg(vals["CES_c"], False), avg(vals["CES_t"], False), avg(vals["CES_p"], False),
                avg(vals["CSAT_c"], True), avg(vals["CSAT_t"], True), avg(vals["CSAT_p"], True),
                str(s), str(dept)
            ]
            annual_table_data.append([process_arabic_text(cell) for cell in row])

        t_annual = Table(annual_table_data, colWidths=col_widths)
        t_annual.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#7b5ab8")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f4f6f9")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        annual_block = KeepTogether([
            Paragraph(process_arabic_text("📊 جدول الملخص السنوي المجمع (المتوسطات):"), section_title_style),
            t_annual
        ])
        elements.append(annual_block)
        elements.append(Spacer(1, 12))

    for p_name, rows in periods_data.items():
        matrix = build_service_matrix(rows)
        period_table_data = [headers]
        for item in matrix:
            row = [
                str(item["Current NPS"]), str(item["Target NPS"]), str(item["Prvious NPS"]),
                str(item["Current CES"]), str(item["Target CES"]), str(item["Prvious CES"]),
                str(item["Current CSAT"]), str(item["Target CSAT"]), str(item["Prvious CSAT"]),
                str(item["Service"]), str(item["Department"])
            ]
            period_table_data.append([process_arabic_text(cell) for cell in row])

        t_period = Table(period_table_data, colWidths=col_widths)
        t_period.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#5a3e8d")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f4f6f9")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        period_block = KeepTogether([
            Paragraph(process_arabic_text(f"📌 جدول بيانات الفترة: {p_name}"), section_title_style),
            t_period
        ])
        elements.append(period_block)
        elements.append(Spacer(1, 12))

    doc.build(elements, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    
    return buffer.getvalue(), f"Report_{period.replace(' ', '_')}.pdf", "application/pdf"