import streamlit as st
import pandas as pd
from style import apply_theme, fix_sidebar_style, COLORS
from database.connection import SessionLocal
from database.models import Section, Service

# تطبيق الثيم والتصميم الموحد
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

# دوال التعامل مع قاعدة البيانات باستخدام SQLAlchemy
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

def delete_department_fully(dept_id):
    session = SessionLocal()
    try:
        # جلب الخدمات التابعة وحذف أي سجلات قياس مرتبطة بها إن وجدت لتجنب التعارض
        services = session.query(Service).filter(Service.section_id == dept_id).all()
        for service in services:
            try:
                from database.models import MeasurementRecord
                session.query(MeasurementRecord).filter(MeasurementRecord.service_id == service.service_id).delete()
            except Exception:
                pass
            session.delete(service)
        
        section = session.get(Section, dept_id)
        if section:
            session.delete(section)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        print(f"Error deleting department: {e}")
        return False
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

def delete_service_fully(service_id):
    session = SessionLocal()
    try:
        # 1. البحث عن جميع سجلات القياس المرتبطة بهذه الخدمة فقط وحذف نتائجها التابعة أولاً
        from database.models import MeasurementRecord, IndicatorResult
        measurement_records = session.query(MeasurementRecord).filter(MeasurementRecord.service_id == service_id).all()
        
        for record in measurement_records:
            # حذف نتائج المؤشرات المرتبطة بسجلات القياس هذه
            session.query(IndicatorResult).filter(IndicatorResult.record_id == record.record_id).delete()
            # حذف سجل القياس نفسه
            session.delete(record)

        # 2. حذف الخدمة المحددة حصراً بناءً على معرفها الفريد (service_id) دون غيرها
        service = session.get(Service, service_id)
        if service:
            session.delete(service)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        print(f"Error deleting service: {e}")
        return False
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

# نافذة منبثقة لتأكيد حذف القسم
@st.dialog("تأكيد الحذف")
def confirm_delete_department_dialog(dept_id, dept_name):
    st.warning(f"هل أنت متأكد من حذف القسم '{dept_name}' وجميع الخدمات التابعة له؟")
    col1, col2 = st.columns(2)
    if col1.button("نعم، حذف", key=f"dialog_del_d_{dept_id}", use_container_width=True):
        if delete_department_fully(dept_id):
            st.success("تم حذف القسم بنجاح!")
            st.rerun()
        else:
            st.error("فشل حذف القسم لوجود بيانات مرتبطة به في النظام.")
    if col2.button("إلغاء", key=f"dialog_cancel_d_{dept_id}", use_container_width=True):
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

# نافذة منبثقة لتأكيد حذف الخدمة
@st.dialog("تأكيد الحذف")
def confirm_delete_service_dialog(service_id, service_name):
    st.warning(f"هل أنت متأكد من حذف الخدمة '{service_name}'؟")
    col1, col2 = st.columns(2)
    if col1.button("نعم، حذف", key=f"dialog_del_s_{service_id}", use_container_width=True):
        if delete_service_fully(service_id):
            st.success("تم حذف الخدمة بنجاح!")
            st.rerun()
        else:
            st.error("فشل حذف الخدمة لوجود بيانات مرتبطة بها في النظام.")
    if col2.button("إلغاء", key=f"dialog_cancel_s_{service_id}", use_container_width=True):
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
                    
                    if b_col1.button("عرض", key=f"view_{row['id']}", use_container_width=True):
                        st.session_state['selected_dept_id'] = row['id']
                        st.session_state['selected_dept_name'] = row['name']
                        st.session_state['page'] = 'services'
                        st.rerun()
                    
                    if b_col2.button("تعديل", key=f"edit_d_{row['id']}", use_container_width=True):
                        st.session_state[f'editing_dept_{row["id"]}'] = True
                        st.rerun()
                    
                    if b_col3.button("حذف", key=f"del_d_{row['id']}", use_container_width=True):
                        confirm_delete_department_dialog(row['id'], row['name'])

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

# صفحة الخدمات التابعة للقسم المحدد
elif st.session_state['page'] == 'services':
    dept_name = st.session_state['selected_dept_name']
    dept_id = st.session_state['selected_dept_id']
    
    if st.button("← العودة للأقسام"):
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
                    
                    if s_col1.button("تعديل", key=f"edit_s_{row['id']}", use_container_width=True):
                        st.session_state[f'editing_serv_{row["id"]}'] = True
                        st.rerun()
                    
                    if s_col2.button("حذف", key=f"del_s_{row['id']}", use_container_width=True):
                        confirm_delete_service_dialog(row['id'], row['name'])

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