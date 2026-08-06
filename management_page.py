import streamlit as st
import pandas as pd
from style import apply_theme, fix_sidebar_style, COLORS
from database.connection import SessionLocal
from database.models import Section, Service

# إعداد الصفحة وتطبيق الثيم الموحد للسايدبار والتصميم[cite: 1]
st.set_page_config(page_title="منصة تجربة العملاء", layout="wide")
apply_theme()
fix_sidebar_style()

# تنسيق إضافي خاص بالاتجاه العربي (RTL) وترتيب الواجهة
st.markdown("""
<style>
    .stApp {
        direction: rtl;
        text-align: right;
    }
    h1, h2, h3, h4, h5, h6, p, span, div {
        text-align: right !important;
        direction: rtl !important;
    }
</style>
""", unsafe_allow_html=True)

# دوال التعامل مع قاعدة البيانات باستخدام SQLAlchemy والـ Models الخاصة بك
def get_departments():
    session = SessionLocal()
    try:
        sections = session.query(Section).all()
        data = [{"id": s.section_id, "name": s.section_name} for s in sections]
        return pd.DataFrame(data)
    finally:
        session.close()

def add_department(name):
    session = SessionLocal()
    try:
        section = Section(section_name=name)
        session.add(section)
        session.commit()
        return True
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()

def update_department(dept_id, new_name):
    session = SessionLocal()
    try:
        section = session.get(Section, dept_id)
        if section:
            section.section_name = new_name
            session.commit()
    finally:
        session.close()

def delete_department(dept_id):
    session = SessionLocal()
    try:
        section = session.get(Section, dept_id)
        if section:
            session.delete(section)
            session.commit()
    finally:
        session.close()

def get_services(dept_id):
    session = SessionLocal()
    try:
        services = session.query(Service).filter(Service.section_id == dept_id).all()
        data = [{"id": s.service_id, "department_id": s.section_id, "name": s.service_name} for s in services]
        return pd.DataFrame(data)
    finally:
        session.close()

def add_service(dept_id, name):
    session = SessionLocal()
    try:
        service = Service(section_id=dept_id, service_name=name)
        session.add(service)
        session.commit()
    finally:
        session.close()

def update_service(service_id, new_name):
    session = SessionLocal()
    try:
        service = session.get(Service, service_id)
        if service:
            service.service_name = new_name
            session.commit()
    finally:
        session.close()

def delete_service(service_id):
    session = SessionLocal()
    try:
        service = session.get(Service, service_id)
        if service:
            session.delete(service)
            session.commit()
    finally:
        session.close()

# نافذة منبثقة لإضافة قسم جديد
@st.dialog("إضافة قسم جديد")
def add_department_dialog():
    with st.form("dialog_add_dept_form"):
        new_dept_name = st.text_input("اسم القسم")

        col1, col2 = st.columns(2)
        submitted = col1.form_submit_button("إضافة", use_container_width=True)
        cancelled = col2.form_submit_button("إلغاء", use_container_width=True)
        
        if submitted:
            if new_dept_name.strip():
                if add_department(new_dept_name.strip()):
                    st.success("تم إضافة القسم بنجاح!")
                    st.rerun()
                else:
                    st.error("اسم القسم موجود مسبقاً!")
            else:
                st.warning("الرجاء إدخال اسم القسم.")
                
        if cancelled:
            st.rerun()

# نافذة منبثقة لإضافة خدمة جديدة
@st.dialog("إضافة خدمة جديدة")
def add_service_dialog(dept_id):
    with st.form("dialog_add_serv_form"):
        new_serv_name = st.text_input("اسم الخدمة")

        col1, col2 = st.columns(2)
        submitted = col1.form_submit_button("إضافة", use_container_width=True)
        cancelled = col2.form_submit_button("إلغاء", use_container_width=True)
        
        if submitted:
            if new_serv_name.strip():
                add_service(dept_id, new_serv_name.strip())
                st.success("تم إضافة الخدمة بنجاح!")
                st.rerun()
            else:
                st.warning("الرجاء إدخال اسم الخدمة.")
                
        if cancelled:
            st.rerun()

# إدارة التنقل بين الصفحات في الجلسة
if 'page' not in st.session_state:
    st.session_state['page'] = 'departments'
if 'selected_dept_id' not in st.session_state:
    st.session_state['selected_dept_id'] = None
if 'selected_dept_name' not in st.session_state:
    st.session_state['selected_dept_name'] = ""

# صفحة الأقسام الرئيسية
if st.session_state['page'] == 'departments':
    st.markdown(f"<h2 style='color: {COLORS['navy']};'>التعديل</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: {COLORS['muted']};'>إضافة، تعديل، وحذف الأقسام المتاحة في النظام</p>", unsafe_allow_html=True)
    
    if st.button("+ إضافة قسم جديد"):
        add_department_dialog()

    st.markdown("---")
    
    depts_df = get_departments()
    
    if depts_df.empty:
        st.info("لا توجد أقسام مضافة حالياً. استخدم زر 'إضافة قسم جديد' للبدء.")
    else:
        cols = st.columns(2)
        for index, row in depts_df.iterrows():
            with cols[index % 2]:
                with st.container(border=True):
                    st.markdown(f"""
                    <div style="text-align: right; direction: rtl;">
                        <h3 style="color: {COLORS['navy']}; margin-bottom: 5px; text-align: right;">{row['name']}</h3>
                        <p style="color: {COLORS['muted']}; font-size: 14px; text-align: right; margin-bottom: 15px;">معرف القسم: #{row['id']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    b_col1, b_col2, b_col3 = st.columns(3)
                    
                    if b_col1.button(" عرض", key=f"view_{row['id']}", use_container_width=True):
                        for key in list(st.session_state.keys()):
                            if key.startswith('deleting_') or key.startswith('editing_'):
                                st.session_state[key] = False
                        st.session_state['selected_dept_id'] = row['id']
                        st.session_state['selected_dept_name'] = row['name']
                        st.session_state['page'] = 'services'
                        st.rerun()
                    
                    if b_col2.button(" تعديل", key=f"edit_d_{row['id']}", use_container_width=True):
                        st.session_state[f'editing_dept_{row["id"]}'] = True
                        st.session_state[f'deleting_dept_{row["id"]}'] = False
                        st.rerun()
                    
                    if b_col3.button(" حذف", key=f"del_d_{row['id']}", use_container_width=True):
                        st.session_state[f'deleting_dept_{row["id"]}'] = True
                        st.session_state[f'editing_dept_{row["id"]}'] = False
                        st.rerun()

                    if st.session_state.get(f'editing_dept_{row["id"]}', False):
                        with st.form(f"edit_dept_form_{row['id']}"):
                            updated_name = st.text_input("اسم القسم الجديد", value=row['name'])
                            e_col1, e_col2 = st.columns(2)
                            if e_col1.form_submit_button("حفظ التعديل", use_container_width=True):
                                update_department(row['id'], updated_name)
                                st.session_state[f'editing_dept_{row["id"]}'] = False
                                st.rerun()
                            if e_col2.form_submit_button("إلغاء", use_container_width=True):
                                st.session_state[f'editing_dept_{row["id"]}'] = False
                                st.rerun()

                    if st.session_state.get(f'deleting_dept_{row["id"]}', False):
                        st.warning(f"هل أنت متأكد من حذف القسم '{row['name']}' وجميع خدماته؟")
                        d_col1, d_col2 = st.columns(2)
                        if d_col1.button("نعم، حذف", key=f"confirm_del_d_{row['id']}", use_container_width=True):
                            delete_department(row['id'])
                            st.session_state[f'deleting_dept_{row["id"]}'] = False
                            st.rerun()
                        if d_col2.button("إلغاء", key=f"cancel_del_d_{row['id']}", use_container_width=True):
                            st.session_state[f'deleting_dept_{row["id"]}'] = False
                            st.rerun()

# صفحة الخدمات التابعة للقسم المحدد
elif st.session_state['page'] == 'services':
    dept_name = st.session_state['selected_dept_name']
    dept_id = st.session_state['selected_dept_id']
    
    if st.button("← العودة للأقسام"):
        for key in list(st.session_state.keys()):
            if key.startswith('deleting_') or key.startswith('editing_'):
                st.session_state[key] = False
        st.session_state['page'] = 'departments'
        st.rerun()
        
    st.markdown(f"<h2 style='color: {COLORS['navy']}; margin-top: 10px;'>خدمات قسم: {dept_name}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: {COLORS['muted']};'>إدارة الخدمات التابعة لهذا القسم</p>", unsafe_allow_html=True)
    
    if st.button("+ إضافة خدمة جديدة"):
        add_service_dialog(dept_id)

    st.markdown("---")
    
    services_df = get_services(dept_id)
    
    if services_df.empty:
        st.info("لا توجد خدمات مضافة تحت هذا القسم حتى الآن.")
    else:
        s_cols = st.columns(2)
        for index, row in services_df.iterrows():
            with s_cols[index % 2]:
                with st.container(border=True):
                    st.markdown(f"""
                    <div style="text-align: right; direction: rtl;">
                        <h3 style="color: {COLORS['navy']}; margin-bottom: 5px; text-align: right;">{row['name']}</h3>
                        <p style="color: {COLORS['muted']}; font-size: 14px; text-align: right; margin-bottom: 15px;">معرف الخدمة: #{row['id']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    s_col1, s_col2 = st.columns(2)
                    
                    if s_col1.button(" تعديل", key=f"edit_s_{row['id']}", use_container_width=True):
                        st.session_state[f'editing_serv_{row["id"]}'] = True
                        st.session_state[f'deleting_serv_{row["id"]}'] = False
                        st.rerun()
                    
                    if s_col2.button(" حذف", key=f"del_s_{row['id']}", use_container_width=True):
                        st.session_state[f'deleting_serv_{row["id"]}'] = True
                        st.session_state[f'editing_serv_{row["id"]}'] = False
                        st.rerun()

                    if st.session_state.get(f'editing_serv_{row["id"]}', False):
                        with st.form(f"edit_serv_form_{row['id']}"):
                            updated_s_name = st.text_input("اسم الخدمة الجديد", value=row['name'])
                            es_col1, es_col2 = st.columns(2)
                            if es_col1.form_submit_button("حفظ التعديل", use_container_width=True):
                                update_service(row['id'], updated_s_name)
                                st.session_state[f'editing_serv_{row["id"]}'] = False
                                st.rerun()
                            if es_col2.form_submit_button("إلغاء", use_container_width=True):
                                st.session_state[f'editing_serv_{row["id"]}'] = False
                                st.rerun()

                    if st.session_state.get(f'deleting_serv_{row["id"]}', False):
                        st.warning(f"هل أنت متأكد تريد حذف هذه الخدمة؟ اسم الخدمة: {row['name']}")
                        ds_col1, ds_col2 = st.columns(2)
                        if ds_col1.button("نعم، حذف", key=f"confirm_del_s_{row['id']}", use_container_width=True):
                            delete_service(row['id'])
                            st.session_state[f'deleting_serv_{row["id"]}'] = False
                            st.rerun()
                        if ds_col2.button("إلغاء", key=f"cancel_del_s_{row['id']}", use_container_width=True):
                            st.session_state[f'deleting_serv_{row["id"]}'] = False
                            st.rerun()