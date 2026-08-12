import streamlit as st
import pymysql
import os
from dotenv import load_dotenv
import sys

# Add current directory path to system path to ensure local module imports work smoothly
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Import custom Excel and PDF report generation functions from local module
from report_generator import generate_excel, generate_pdf

# Load environment variables from a .env file into the application
load_dotenv()

def fetch_period_data_from_mysql(selected_periods):
    """
    Connects to the MySQL database, loops through the selected periods, 
    executes an SQL query to fetch performance indicators and metrics, 
    and handles missing periods or connection exceptions.
    """
    try:
        # Establish connection to MySQL database using environment variables or fallback credentials
        connection = pymysql.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3307)),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', 'COOP@nllr2026'),
            database=os.getenv('DB_NAME', 'customer_experience_db'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        # Initialize dictionaries and lists to hold fetched data and missing periods tracking
        periods_data = {}
        missing_periods = []

        # Open a database cursor context to run queries safely
        with connection.cursor() as cursor:
            for period_str in selected_periods:
                # Split period string (e.g., "2025 - النصف الأول") into separate year and period components
                parts = period_str.split(" - ")
                year_val = parts[0].strip()
                period_val = parts[1].strip()

                # SQL query joining indicator results, measurement records, services, and sections
                query = """
                    SELECT d.SectionName AS DepartmentName, s.ServiceName, res.PrevValue, res.TargetValue, res.CurrentValue, ind.IndicatorName, mr.Year, mr.Period
                    FROM indicatorresults res
                    JOIN indicators ind ON res.IndicatorID = ind.IndicatorID
                    JOIN measurementrecords mr ON res.RecordID = mr.RecordID
                    JOIN service s ON mr.ServiceID = s.ServiceID
                    JOIN section d ON s.SectionID = d.SectionID
                    WHERE mr.Year = %s AND mr.Period = %s
                """
                # Execute the query binding year and period parameters securely
                cursor.execute(query, (year_val, period_val))
                rows = cursor.fetchall()
                
                # Check if records exist; if empty, record it as a missing period, otherwise store data
                if not rows:
                    missing_periods.append(period_str)
                else:
                    periods_data[period_str] = rows

        # Close database connection cleanly
        connection.close()
        
        # Return missing periods if any were found
        if missing_periods:
            return None, missing_periods
            
        # Return compiled data dictionary and empty missing list on success
        return periods_data, []
        
    except Exception as e:
        # Print debug error message and return database connection failure flag
        print(f"DEBUG ERROR: {e}")
        return None, ["خطأ في الاتصال بقاعدة البيانات"]

# Inject custom CSS styles for Streamlit UI (Tajawal font, RTL alignment, container designs)
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

# Render main page title and subtitle description
st.markdown("<h1 style='color: #1e253c; margin-bottom: 0; text-align: right; font-weight: bold;'>التقارير</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #8a94b5; font-size: 16px; margin-bottom: 40px; text-align: right; font-weight: bold;'>تصدير تقرير شامل بالنتائج والتوصيات من قاعدة البيانات</p>", unsafe_allow_html=True)

# Generate a list of periods spanning from year 2020 to 2030 for both halves
periods = [f"{year} - النصف {half}" for year in range(2020, 2031) for half in ["الأول", "الثاني"]]

# Create a Streamlit form block for period and file format selections
with st.form("report_form"):
    st.markdown("<h3 style='color: #1e253c; margin-top: 0; margin-bottom: 20px; text-align: right;'>إنشاء تقرير جديد</h3>", unsafe_allow_html=True)
    
    # Split form layout into two columns for multiselect and selectbox widgets
    col1_right, col2_left = st.columns(2)
    with col1_right:
        selected_periods = st.multiselect("اختر الفترات المطلوبة", periods, placeholder="اضغط لاختيار الفترات...")
    with col2_left:
        selected_format = st.selectbox("الصيغة", ["PDF", "Excel"], index=None, placeholder="اختر الصيغة...")
        
    st.markdown("<br>", unsafe_allow_html=True)
    # Form submit button triggering data collection and generation
    submit_button = st.form_submit_button("تجهيز التقرير", type="primary")

# Execute report compilation logic upon form submission
if submit_button:
    # Validate user inputs to ensure both periods and format are selected
    if not selected_periods or selected_format is None:
        st.error("الرجاء اختيار فترة واحدة على الأقل وتحديد صيغة الملف.")
    else:
        # Fetch target data matching the chosen periods from MySQL
        periods_data, missing_periods = fetch_period_data_from_mysql(selected_periods)
        
        # Handle errors if any selected periods lack data in the database
        if missing_periods:
            st.error(f"تعذر إنشاء التقرير! الفترات التالية ليس لها بيانات مسجلة: {', '.join(missing_periods)}.")
        else:
            st.success("تم تجهيز التقرير بنجاح، اضغط على زر التحميل أدناه.")
            
            # Combine selected period labels using an ampersand separator string
            period_label = " & ".join(selected_periods)
            
            # Generate either Excel or PDF byte contents depending on user format choice
            if selected_format == "Excel":
                file_content, file_name, mime_type = generate_excel(period_label, periods_data)
            else:
                file_content, file_name, mime_type = generate_pdf(period_label, periods_data)
            
            # Render a secure download button for downloading the final generated document file
            st.download_button(
                label="احفظ الملف الآن",
                data=file_content,
                file_name=file_name,
                mime=mime_type,
                type="primary"
            )