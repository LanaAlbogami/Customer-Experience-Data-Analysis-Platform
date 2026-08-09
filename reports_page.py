import streamlit as st
import pymysql
import os
from dotenv import load_dotenv

import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from report_generator import generate_excel, generate_pdf

load_dotenv()

def fetch_period_data_from_mysql(selected_periods):
    try:
        connection = pymysql.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3307)),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', 'COOP@nllr2026'),
            database=os.getenv('DB_NAME', 'customer_experience_db'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        periods_data = {}
        missing_periods = []

        with connection.cursor() as cursor:
            for period_str in selected_periods:
                parts = period_str.split(" - ")
                year_val = parts[0].strip()
                period_val = parts[1].strip()

                # استعلام SQL محدث ومصحح ليتوافق مع مخطط قاعدة البيانات (Schema) الخاص بك
                query = """
                    SELECT d.SectionName AS DepartmentName, s.ServiceName, res.PrevValue, res.TargetValue, res.CurrentValue, ind.IndicatorName, mr.Year, mr.Period
                    FROM indicatorresults res
                    JOIN indicators ind ON res.IndicatorID = ind.IndicatorID
                    JOIN measurementrecords mr ON res.RecordID = mr.RecordID
                    JOIN service s ON mr.ServiceID = s.ServiceID
                    JOIN section d ON s.SectionID = d.SectionID
                    WHERE mr.Year = %s AND mr.Period = %s
                """
                cursor.execute(query, (year_val, period_val))
                rows = cursor.fetchall()
                
                if not rows:
                    missing_periods.append(period_str)
                else:
                    periods_data[period_str] = rows

        connection.close()
        
        if missing_periods:
            return None, missing_periods
            
        return periods_data, []
        
    except Exception as e:
        print(f"DEBUG ERROR: {e}")
        return None, ["خطأ في الاتصال بقاعدة البيانات"]

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');
    .stApp, .stApp * { font-family: 'Tajawal', sans-serif !important; direction: rtl; text-align: right !important; }
    [data-testid="stAppViewContainer"] { background-color: #f4f6f9; }
    [data-testid="stForm"] { background-color: white; border: none; border-radius: 15px; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    button[kind="primary"] { background-color: #7b5ab8 !important; color: White !important; border: none !important; border-radius: 8px !important; padding: 10px 40px !important; font-weight: 600 !important; float: right !important; }
    button[kind="primary"]:hover { background-color: #6a4da0 !important; }
    .stMultiSelect div[data-baseweb="select"] { background-color: white; border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("<h1 style='color: #1e253c; margin-bottom: 0; text-align: right; font-weight: bold;'>التقارير</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #8a94b5; font-size: 16px; margin-bottom: 40px; text-align: right; font-weight: bold;'>تصدير تقرير شامل بالنتائج والتوصيات من قاعدة البيانات</p>", unsafe_allow_html=True)

periods = [f"{year} - النصف {half}" for year in range(2020, 2031) for half in ["الأول", "الثاني"]]

with st.form("report_form"):
    st.markdown("<h3 style='color: #1e253c; margin-top: 0; margin-bottom: 20px; text-align: right;'>إنشاء تقرير جديد</h3>", unsafe_allow_html=True)
    
    col1_right, col2_left = st.columns(2)
    with col1_right:
        selected_periods = st.multiselect("اختر الفترات المطلوبة", periods, placeholder="اضغط لاختيار الفترات...")
    with col2_left:
        selected_format = st.selectbox("الصيغة", ["PDF", "Excel"], index=None, placeholder="اختر الصيغة...")
        
    st.markdown("<br>", unsafe_allow_html=True)
    submit_button = st.form_submit_button("تجهيز التقرير", type="primary")

if submit_button:
    if not selected_periods or selected_format is None:
        st.error(" الرجاء اختيار فترة واحدة على الأقل وتحديد صيغة الملف.")
    else:
        periods_data, missing_periods = fetch_period_data_from_mysql(selected_periods)
        
        if missing_periods:
            st.error(f" تعذر إنشاء التقرير! الفترات التالية ليس لها بيانات مسجلة : {', '.join(missing_periods)}.")
        else:
            st.success("  تم تجهيز التقرير بنجاح، اضغط على زر التحميل أدناه.")
            
            period_label = " & ".join(selected_periods)
            
            if selected_format == "Excel":
                file_content, file_name, mime_type = generate_excel(period_label, periods_data)
            else:
                file_content, file_name, mime_type = generate_pdf(period_label, periods_data)
            
            st.download_button(
                label=" احفظ الملف الآن",
                data=file_content,
                file_name=file_name,
                mime=mime_type,
                type="primary"
            )


