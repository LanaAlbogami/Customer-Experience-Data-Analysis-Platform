# Import the Streamlit library for building interactive web applications
import streamlit as st

# Import the Pandas library for data manipulation and handling DataFrames
import pandas as pd

# Import custom theme application functions, sidebar fixer, and color constants from the local style module
from style import apply_theme, fix_sidebar_style, COLORS

# Import the SQLAlchemy database session local maker from the database connection module
from database.connection import SessionLocal

# Import SQLAlchemy database models representing Sections (Departments) and Services
from database.models import Section, Service

# Invoke the apply_theme function to set up global styling parameters for the application
apply_theme()

# Invoke the fix_sidebar_style function to align and correct sidebar appearance and layout
fix_sidebar_style()

# Inject custom CSS code into the Streamlit app to enforce Right-to-Left (RTL) direction and text alignment
st.markdown("""
<style>
    /* Force the main Streamlit application container to display content in RTL direction with right-aligned text */
    .stApp {
        direction: rtl;
        text-align: right;
    }
    /* Enforce right alignment and RTL direction across all headings, paragraphs, spans, and generic container elements */
    h1, h2, h3, h4, h5, h6, p, span, div {
        text-align: right !important;
        direction: rtl !important;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# DATABASE OPERATION FUNCTIONS (Departments / Sections Management)
# -------------------------------------------------------------------------

def get_departments():
    """
    Query all Section records from the database and package them 
    into a Pandas DataFrame containing section IDs and names.
    """
    # Create a new local database session instance
    session = SessionLocal()
    try:
        # Query all rows from the Section table
        sections = session.query(Section).all()
        # Convert SQLAlchemy section objects into a list of dictionaries
        data = [{"id": s.section_id, "name": s.section_name} for s in sections]
        # Return the collected data structured as a Pandas DataFrame
        return pd.DataFrame(data)
    finally:
        # Ensure the database session is closed safely after execution
        session.close()

def add_department(name):
    """
    Create and insert a new Section record into the database 
    using the provided department name string.
    """
    # Initialize a new database session
    session = SessionLocal()
    try:
        # Instantiate a new Section model object with the given name
        section = Section(section_name=name)
        # Add the new section instance to the active session staging area
        session.add(section)
        # Commit the transaction to persist changes permanently in the database
        session.commit()
        # Return True indicating successful addition
        return True
    except Exception:
        # Roll back the transaction in case of any database integrity or connection errors
        session.rollback()
        # Return False indicating the operation failed
        return False
    finally:
        # Always close the active session to free connection resources
        session.close()

def update_department(dept_id, new_name):
    """
    Fetch an existing department by its primary key ID and update 
    its name with the newly provided string value.
    """
    # Open a new database session context
    session = SessionLocal()
    try:
        # Retrieve the Section object matching the specified primary key ID
        section = session.get(Section, dept_id)
        # Check if the section record exists in the database
        if section:
            # Update the section name attribute with the new value
            section.section_name = new_name
            # Commit the update transaction to the database
            session.commit()
    finally:
        # Close the database session safely
        session.close()

def delete_department_fully(dept_id):
    """
    Completely delete a department along with all its dependent services 
    and associated measurement records to avoid foreign key violations.
    """
    # Initialize a new database session
    session = SessionLocal()
    try:
        # Query all services linked to this specific department ID
        services = session.query(Service).filter(Service.section_id == dept_id).all()
        # Iterate through each dependent service to clean up its child records first
        for service in services:
            try:
                # Import MeasurementRecord model locally to avoid circular dependencies
                from database.models import MeasurementRecord
                # Delete any measurement records tied to this service ID
                session.query(MeasurementRecord).filter(MeasurementRecord.service_id == service.service_id).delete()
            except Exception:
                pass
            # Delete the service record itself from the database session
            session.delete(service)
        
        # Retrieve the target department section object by its ID
        section = session.get(Section, dept_id)
        # Verify that the section exists before attempting deletion
        if section:
            # Delete the section record from the session
            session.delete(section)
            # Commit all deletion transactions permanently
            session.commit()
            # Return True to signal successful complete deletion
            return True
        return False
    except Exception as e:
        # Rollback changes if an error occurs during cascading deletion
        session.rollback()
        # Print out the debug error message to the console
        print(f"Error deleting department: {e}")
        return False
    finally:
        # Close the database session connection
        session.close()

# -------------------------------------------------------------------------
# DATABASE OPERATION FUNCTIONS (Services Management)
# -------------------------------------------------------------------------

def get_services(dept_id):
    """
    Retrieve all service records associated with a specific department (section) ID 
    and return them packaged inside a Pandas DataFrame.
    """
    # Open a fresh database session
    session = SessionLocal()
    try:
        # Query all Service items matching the given section ID foreign key
        services = session.query(Service).filter(Service.section_id == dept_id).all()
        # Map service properties into a structured list of dictionaries
        data = [{"id": s.service_id, "department_id": s.section_id, "name": s.service_name} for s in services]
        # Return the data formatted as a Pandas DataFrame
        return pd.DataFrame(data)
    finally:
        # Close the session securely
        session.close()

def add_service(dept_id, name):
    """
    Insert a new service record into the database linked to 
    the specified department (section) ID.
    """
    # Create a database session
    session = SessionLocal()
    try:
        # Create a new Service model instance linking the section ID and service name
        service = Service(section_id=dept_id, service_name=name)
        # Stage the new service instance in the session
        session.add(service)
        # Commit the transaction to save it in the database
        session.commit()
    finally:
        # Close the session connection
        session.close()

def update_service(service_id, new_name):
    """
    Update the name attribute of an existing service record 
    identified by its unique primary key ID.
    """
    # Open a new database session
    session = SessionLocal()
    try:
        # Fetch the Service object using its primary key ID
        service = session.get(Service, service_id)
        # Check if the service record exists
        if service:
            # Update the service name field with the new value string
            service.service_name = new_name
            # Commit the changes to the database
            session.commit()
    finally:
        # Close the session safely
        session.close()

def delete_service_fully(service_id):
    """
    Safely delete a specific service by purging its dependent measurement records 
    and related indicator results beforehand to prevent foreign key errors.
    """
    # Initialize a new database session
    session = SessionLocal()
    try:
        # Import MeasurementRecord and IndicatorResult models locally
        from database.models import MeasurementRecord, IndicatorResult
        # Query all measurement records linked to this particular service ID
        measurement_records = session.query(MeasurementRecord).filter(MeasurementRecord.service_id == service_id).all()
        
        # Loop through each measurement record to delete child indicator results first
        for record in measurement_records:
            # Delete indicator response results tied to this record's primary key ID
            session.query(IndicatorResult).filter(IndicatorResult.record_id == record.record_id).delete()
            # Delete the measurement record itself from the session
            session.delete(record)

        # Fetch the target service record by its unique identifier primary key
        service = session.get(Service, service_id)
        # Verify the service exists before deletion
        if service:
            # Delete the service object from the active session
            session.delete(service)
            # Commit the final transaction to the database
            session.commit()
            # Return True to indicate success
            return True
        return False
    except Exception as e:
        # Roll back database modifications on error
        session.rollback()
        # Print the exception details for debugging purposes
        print(f"Error deleting service: {e}")
        return False
    finally:
        # Close the database session connection
        session.close()

# -------------------------------------------------------------------------
# STREAMLIT INTERACTIVE DIALOG WINDOWS (Modals)
# -------------------------------------------------------------------------

# Define a Streamlit modal dialog window for adding a new department
@st.dialog("إضافة قسم جديد")
def add_department_dialog():
    """Render a modal input form allowing users to input and submit a new department name."""
    # Create an input form container block for adding departments
    with st.form("dialog_add_dept_form"):
        # Render a text input field for the new department name
        new_dept_name = st.text_input("اسم القسم")

        # Split the form layout into two equal columns for buttons
        col1, col2 = st.columns(2)
        # Create submission button inside column 1
        submitted = col1.form_submit_button("إضافة", use_container_width=True)
        # Create cancellation button inside column 2
        cancelled = col2.form_submit_button("إلغاء", use_container_width=True)
        
        # Handle form submission action logic
        if submitted:
            # Check if the entered department name string is not empty after stripping whitespace
            if new_dept_name.strip():
                # Attempt to add the department and verify if it succeeds
                if add_department(new_dept_name.strip()):
                    st.success("تم إضافة القسم بنجاح!")
                    st.rerun()
                else:
                    st.error("اسم القسم موجود مسبقاً!")
            else:
                st.warning("الرجاء إدخال اسم القسم.")
                
        # Handle cancellation button click action
        if cancelled:
            st.rerun()

# Define a Streamlit modal dialog window to confirm department deletion
@st.dialog("تأكيد الحذف")
def confirm_delete_department_dialog(dept_id, dept_name):
    """Render a warning confirmation dialog before completely deleting a department."""
    # Display a warning alert message showing the name of the department targeted for deletion
    st.warning(f"هل أنت متأكد من حذف القسم '{dept_name}' وجميع الخدمات التابعة له؟")
    # Divide the dialog layout into two columns for action buttons
    col1, col2 = st.columns(2)
    # Check if the confirmation delete button was clicked
    if col1.button("نعم، حذف", key=f"dialog_del_d_{dept_id}", use_container_width=True):
        # Trigger full deletion of the department and check success status
        if delete_department_fully(dept_id):
            st.success("تم حذف القسم بنجاح!")
            st.rerun()
        else:
            st.error("فشل حذف القسم لوجود بيانات مرتبطة به في النظام.")
    # Check if the cancellation button was clicked
    if col2.button("إلغاء", key=f"dialog_cancel_d_{dept_id}", use_container_width=True):
        st.rerun()

# Define a Streamlit modal dialog window for adding a new service under a specific department
@st.dialog("إضافة خدمة جديدة")
def add_service_dialog(dept_id):
    """Render a modal input form allowing users to add a new service linked to a given department ID."""
    # Create a form container block for adding services
    with st.form("dialog_add_serv_form"):
        # Render a text input box for typing the service name
        new_serv_name = st.text_input("اسم الخدمة")

        # Create two columns for form action buttons
        col1, col2 = st.columns(2)
        # Submit button in column 1
        submitted = col1.form_submit_button("إضافة", use_container_width=True)
        # Cancel button in column 2
        cancelled = col2.form_submit_button("إلغاء", use_container_width=True)
        
        # Process form submission
        if submitted:
            # Validate that the service name input is not blank
            if new_serv_name.strip():
                add_service(dept_id, new_serv_name.strip())
                st.success("تم إضافة الخدمة بنجاح!")
                st.rerun()
            else:
                st.warning("الرجاء إدخال اسم الخدمة.")
                
        # Process cancellation action
        if cancelled:
            st.rerun()

# Define a Streamlit modal dialog window to confirm service deletion
@st.dialog("تأكيد الحذف")
def confirm_delete_service_dialog(service_id, service_name):
    """Render a warning confirmation dialog before permanently deleting a specific service."""
    # Display a warning confirmation prompt featuring the name of the service
    st.warning(f"هل أنت متأكد من حذف الخدمة '{service_name}'؟")
    # Split layout into two columns
    col1, col2 = st.columns(2)
    # Execute service deletion if confirmed
    if col1.button("نعم، حذف", key=f"dialog_del_s_{service_id}", use_container_width=True):
        if delete_service_fully(service_id):
            st.success("تم حذف الخدمة بنجاح!")
            st.rerun()
        else:
            st.error("فشل حذف الخدمة لوجود بيانات مرتبطة به في النظام.")
    # Cancel action button
    if col2.button("إلغاء", key=f"dialog_cancel_s_{service_id}", use_container_width=True):
        st.rerun()

# -------------------------------------------------------------------------
# SESSION STATE NAVIGATION & CONTEXT INITIALIZATION
# -------------------------------------------------------------------------

# Initialize session state tracking variable for the current active page view if not already set
if 'page' not in st.session_state:
    st.session_state['page'] = 'departments'

# Initialize session state variable to store the currently selected department primary key ID
if 'selected_dept_id' not in st.session_state:
    st.session_state['selected_dept_id'] = None

# Initialize session state variable to store the name string of the selected department context
if 'selected_dept_name' not in st.session_state:
    st.session_state['selected_dept_name'] = ""

# -------------------------------------------------------------------------
# PAGE VIEW ROUTING: DEPARTMENTS MANAGEMENT VIEW
# -------------------------------------------------------------------------

# Check if the active application state points to the main departments page view
if st.session_state['page'] == 'departments':
    # Render the section header title styled using predefined color themes
    st.markdown(f"<h2 style='color: {COLORS['navy']};'>التعديل</h2>", unsafe_allow_html=True)
    # Render a subtitle description text paragraph below the header
    st.markdown(f"<p style='color: {COLORS['muted']};'>إضافة، تعديل، وحذف الأقسام المتاحة في النظام</p>", unsafe_allow_html=True)
    
    # Render a primary action button to open the add department dialog modal
    if st.button("+ إضافة قسم جديد"):
        add_department_dialog()

    # Render a horizontal divider separator line across the page layout
    st.markdown("---")
    
    # Fetch all department records from the database into a Pandas DataFrame
    depts_df = get_departments()
    
    # Check if the departments DataFrame is empty (no records found)
    if depts_df.empty:
        # Display an informational message box prompting the user to add departments
        st.info("لا توجد أقسام مضافة حالياً. استخدم زر 'إضافة قسم جديد' للبدء.")
    else:
        # Create a two-column grid layout configuration for listing departments
        cols = st.columns(2)
        # Iterate through each department row inside the DataFrame along with its index position
        for index, row in depts_df.iterrows():
            # Place each department card inside alternating grid columns using modulus operator
            with cols[index % 2]:
                # Wrap each department record inside a framed container card element
                with st.container(border=True):
                    # Render the department name heading and its unique database identifier text
                    st.markdown(f"""
                    <div style="text-align: right; direction: rtl;">
                        <h3 style="color: {COLORS['navy']}; margin-bottom: 5px; text-align: right;">{row['name']}</h3>
                        <p style="color: {COLORS['muted']}; font-size: 14px; text-align: right; margin-bottom: 15px;">معرف القسم: #{row['id']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Create a three-column layout inside the card for action buttons (View, Edit, Delete)
                    b_col1, b_col2, b_col3 = st.columns(3)
                    
                    # Render the 'View' button to navigate to the services management page for this department
                    if b_col1.button("عرض", key=f"view_{row['id']}", use_container_width=True):
                        st.session_state['selected_dept_id'] = row['id']
                        st.session_state['selected_dept_name'] = row['name']
                        st.session_state['page'] = 'services'
                        st.rerun()
                    
                    # Render the 'Edit' button to trigger inline editing state for this specific department card
                    if b_col2.button("تعديل", key=f"edit_d_{row['id']}", use_container_width=True):
                        st.session_state[f'editing_dept_{row["id"]}'] = True
                        st.rerun()
                    
                    # Render the 'Delete' button to trigger the confirmation dialog modal for this department
                    if b_col3.button("حذف", key=f"del_d_{row['id']}", use_container_width=True):
                        confirm_delete_department_dialog(row['id'], row['name'])

                    # Check if the inline edit state session flag is currently active for this department row
                    if st.session_state.get(f'editing_dept_{row["id"]}', False):
                        # Render an inline form container for modifying the department name
                        with st.form(f"edit_dept_form_{row['id']}"):
                            updated_name = st.text_input("اسم القسم الجديد", value=row['name'])
                            e_col1, e_col2 = st.columns(2)
                            # Handle save update form button click
                            if e_col1.form_submit_button("حفظ التعديل", use_container_width=True):
                                update_department(row['id'], updated_name)
                                st.session_state[f'editing_dept_{row["id"]}'] = False
                                st.rerun()
                            # Handle cancel inline edit button click
                            if e_col2.form_submit_button("إلغاء", use_container_width=True):
                                st.session_state[f'editing_dept_{row["id"]}'] = False
                                st.rerun()

# -------------------------------------------------------------------------
# PAGE VIEW ROUTING: SERVICES MANAGEMENT VIEW
# -------------------------------------------------------------------------

# Check if the active application state points to the services management page view
elif st.session_state['page'] == 'services':
    # Retrieve the currently selected department name and ID strings from session state context
    dept_name = st.session_state['selected_dept_name']
    dept_id = st.session_state['selected_dept_id']
    
    # Render a navigation back button allowing users to return to the main departments view
    if st.button("← العودة للأقسام"):
        st.session_state['page'] = 'departments'
        st.rerun()
        
    # Render the section header title displaying the active department context name
    st.markdown(f"<h2 style='color: {COLORS['navy']}; margin-top: 10px;'>خدمات قسم: {dept_name}</h2>", unsafe_allow_html=True)
    # Render descriptive subtitle text below the service header
    st.markdown(f"<p style='color: {COLORS['muted']};'>إدارة الخدمات التابعة لهذا القسم</p>", unsafe_allow_html=True)
    
    # Render action button to open the add service dialog modal popup window
    if st.button("+ إضافة خدمة جديدة"):
        add_service_dialog(dept_id)

    # Render a separator divider line
    st.markdown("---")
    
    # Fetch all services associated with the selected department ID into a Pandas DataFrame
    services_df = get_services(dept_id)
    
    # Check if the services DataFrame is empty
    if services_df.empty:
        # Display an information box when no services are currently registered under this department
        st.info("لا توجد خدمات مضافة تحت هذا القسم حتى الآن.")
    else:
        # Create a two-column grid layout configuration for rendering service cards
        s_cols = st.columns(2)
        # Iterate through each row in the services DataFrame
        for index, row in services_df.iterrows():
            # Distribute service cards across alternating grid columns using modulus operator
            with s_cols[index % 2]:
                # Wrap each service record inside a bordered container card element
                with st.container(border=True):
                    # Render service name header and its primary key ID string
                    st.markdown(f"""
                    <div style="text-align: right; direction: rtl;">
                        <h3 style="color: {COLORS['navy']}; margin-bottom: 5px; text-align: right;">{row['name']}</h3>
                        <p style="color: {COLORS['muted']}; font-size: 14px; text-align: right; margin-bottom: 15px;">معرف الخدمة: #{row['id']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Create a two-column layout for service action buttons (Edit and Delete)
                    s_col1, s_col2 = st.columns(2)
                    
                    # Render the 'Edit' button to trigger inline editing state for this specific service card
                    if s_col1.button("تعديل", key=f"edit_s_{row['id']}", use_container_width=True):
                        st.session_state[f'editing_serv_{row["id"]}'] = True
                        st.rerun()
                    
                    # Render the 'Delete' button to trigger the confirmation dialog modal for this service
                    if s_col2.button("حذف", key=f"del_s_{row['id']}", use_container_width=True):
                        confirm_delete_service_dialog(row['id'], row['name'])

                    # Check if the inline edit flag is active for this particular service row item
                    if st.session_state.get(f'editing_serv_{row["id"]}', False):
                        # Render an inline modification form container
                        with st.form(f"edit_serv_form_{row['id']}"):
                            updated_s_name = st.text_input("اسم الخدمة الجديد", value=row['name'])
                            es_col1, es_col2 = st.columns(2)
                            # Handle save update action click
                            if es_col1.form_submit_button("حفظ التعديل", use_container_width=True):
                                update_service(row['id'], updated_s_name)
                                st.session_state[f'editing_serv_{row["id"]}'] = False
                                st.rerun()
                            # Handle cancel action click
                            if es_col2.form_submit_button("إلغاء", use_container_width=True):
                                st.session_state[f'editing_serv_{row["id"]}'] = False
                                st.rerun()