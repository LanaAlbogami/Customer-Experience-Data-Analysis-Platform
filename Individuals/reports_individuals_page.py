import streamlit as st
import pymysql
import os
from dotenv import load_dotenv
import sys

# Append the current directory to system path to enable importing local custom modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Import PDF and Excel generator functions designated for individual reports from a local module
from report_individuals_generator import generate_excel, generate_pdf

# Load environment configuration variables from the .env file
load_dotenv()

def fetch_summary_data_from_mysql(selected_periods):
    """
    Connects to the MySQL database to query measurement metrics, indicator responses, 
    and CSAT factors for each period selected by the user.
    """
    try:
        # Establish connection to the individuals experience database using environment parameters
        connection = pymysql.connect(
            host='localhost',
            port=int(os.getenv("DB_PORT")),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME_INDIVIDUALS'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        # Initialize dictionaries to hold period indicators/factors data and a tracking list for missing data
        periods_data = {}
        factors_data = {}
        missing_periods = []

        # Open a database cursor context to execute queries safely
        with connection.cursor() as cursor:
            for period_str in selected_periods:
                # Parse and split the period string into year and specific quarter text
                parts = period_str.split(" - ")
                year_val = int(parts[0].strip())
                period_val = parts[1].strip()

                # 1. Query to fetch CES and NPS indicators and values for individuals
                query = """
                    SELECT 
                        ind.IndicatorName,
                        res.RatingValue AS CurrentValue,
                        mr.Year, 
                        mr.Period
                    FROM individualmeasurementrecords mr
                    JOIN individualindicatorresponses res ON mr.RecordID = res.RecordID
                    JOIN sharedindicators ind ON res.IndicatorID = ind.IndicatorID
                    WHERE mr.Year = %s AND mr.Period = %s
                """
                cursor.execute(query, (year_val, period_val))
                rows = cursor.fetchall()
                
                # 2. Query to fetch the 8 CSAT factors and their rating responses
                factor_query = """
                    SELECT 
                        f.FactorName,
                        fr.RatingValue
                    FROM individualmeasurementrecords mr
                    JOIN individualfactorresponses fr ON mr.RecordID = fr.RecordID
                    JOIN sharedcsatfactors f ON fr.FactorID = f.FactorID
                    WHERE mr.Year = %s AND mr.Period = %s
                """
                cursor.execute(factor_query, (year_val, period_val))
                f_rows = cursor.fetchall()
                
                # Check if data exists for the current loop iteration; track if missing or map it
                if not rows and not f_rows:
                    missing_periods.append(period_str)
                else:
                    periods_data[period_str] = rows
                    factors_data[period_str] = f_rows

        # Safely close the database connection
        connection.close()
        
        # Return missing periods indicator if any requested period lacks database records
        if missing_periods:
            return None, None, missing_periods
            
        # Return successfully compiled data dictionaries and an empty missing list
        return periods_data, factors_data, []
        
    except Exception as e:
        # Catch and print connection or execution errors, returning a standard error flag list
        print(f"DEBUG ERROR: {e}")
        return None, None, ["خطأ في الاتصال بقاعدة البيانات"]

# Apply custom CSS styling injections for the Streamlit UI (Tajawal font, RTL alignment, container layouts)
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

# Render main header title and description texts for the individual reports view
st.markdown("<h1 style='color: #1e253c; margin-bottom: 0; text-align: right; font-weight: bold;'>تقارير الأفراد</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #8a94b5; font-size: 16px; margin-bottom: 40px; text-align: right; font-weight: bold;'>تصدير ملخص النتائج النهائية للمؤشرات وعوامل رضا العملاء</p>", unsafe_allow_html=True)

# Generate a list of available quarter-based periods spanning from 2020 through 2030
periods = [f"{year} - الربع {quarter}" for year in range(2020, 2031) for quarter in ["الأول", "الثاني", "الثالث", "الرابع"]]

# Create a Streamlit form container for user input fields selection
with st.form("report_form"):
    st.markdown("<h3 style='color: #1e253c; margin-top: 0; margin-bottom: 20px; text-align: right;'>إنشاء ملخص التقرير النهائي</h3>", unsafe_allow_html=True)
    
    # Split the form layout into two columns: one for period selection, one for file format choice
    col1_right, col2_left = st.columns(2)
    with col1_right:
        selected_periods = st.multiselect("اختر الفترات المطلوبة", periods, placeholder="اضغط لاختيار الفترات...")
    with col2_left:
        selected_format = st.selectbox("الصيغة", ["PDF", "Excel"], index=None, placeholder="اختر الصيغة...")
        
    st.markdown("<br>", unsafe_allow_html=True)
    # Form submission button triggering the generation workflow
    submit_button = st.form_submit_button("تجهيز التقرير", type="primary")

# Execute report generation logic when the form submit button is clicked
if submit_button:
    # Validate that the user has selected at least one period and chosen a file format
    if not selected_periods or selected_format is None:
        st.error("الرجاء اختيار فترة واحدة على الأقل وتحديد صيغة الملف.")
    else:
        # Helper sorting function to order periods chronologically from oldest to newest
        def sort_period_key(p_str):
            try:
                parts = p_str.split(" - ")
                year = int(parts[0].strip())
                q_text = parts[1].strip()
                q_map = {"الربع الأول": 1, "الربع الثاني": 2, "الربع الثالث": 3, "الربع الرابع": 4}
                return (year, q_map.get(q_text, 0))
            except:
                return (0, 0)

        # Sort the selected periods list in ascending chronological order
        sorted_periods = sorted(selected_periods, key=sort_period_key)

        # Retrieve summary data records from MySQL using the sorted periods list
        periods_data, factors_data, missing_periods = fetch_summary_data_from_mysql(sorted_periods)
        
        # Display an error alert if any of the selected periods lack recorded database data
        if missing_periods:
            st.error(f"تعذر إنشاء التقرير! الفترات التالية ليس لها بيانات مسجلة: {', '.join(missing_periods)}.")
        else:
            st.success("تم تجهيز التقرير النهائي بنجاح، اضغط على زر التحميل أدناه.")
            
            # Combine the sorted period labels into a unified string separated by an ampersand
            period_label = " & ".join(sorted_periods)
            
            # Reconstruct and order data dictionaries to strictly match the sorted sequence
            ordered_periods_data = {p: periods_data[p] for p in sorted_periods if p in periods_data}
            ordered_factors_data = {p: factors_data[p] for p in sorted_periods if p in factors_data}
            
            # Generate binary file contents using either the Excel or PDF generator functions
            if selected_format == "Excel":
                file_content, file_name, mime_type = generate_excel(period_label, ordered_periods_data, ordered_factors_data)
            else:
                file_content, file_name, mime_type = generate_pdf(period_label, ordered_periods_data, ordered_factors_data)
            
            # Render a download button allowing the user to download the generated file securely
            st.download_button(
                label="احفظ الملف الآن",
                data=file_content,
                file_name=file_name,
                mime=mime_type,
                type="primary"
            )