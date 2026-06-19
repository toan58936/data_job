# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from collections import Counter
import numpy as np
import ast

st.set_page_config(page_title="Data Job Market Dashboard", layout="wide")
st.title("📊 Hệ thống dữ liệu tuyển dụng ngành Data tại Việt Nam")
st.markdown("---")

# Hàm chuyển đổi an toàn sang list
def to_list(x):
    if isinstance(x, list):
        return x
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, str):
        try:
            # Xử lý chuỗi dạng "['a', 'b']"
            return ast.literal_eval(x) if x.startswith('[') else []
        except:
            return []
    return []

# Load dữ liệu
@st.cache_data
def load_data():
    df = pd.read_parquet("data/silver/jobs_silver.parquet")
    # Chuyển skills và domain_keywords thành list
    df['skills'] = df['skills'].apply(to_list)
    df['domain_keywords'] = df['domain_keywords'].apply(to_list)
    return df

df = load_data()

# Sidebar filters
st.sidebar.header("Bộ lọc")
roles = st.sidebar.multiselect(
    "Chọn vai trò (normalized_role)",
    options=sorted(df['normalized_role'].unique()),
    default=sorted(df['normalized_role'].unique())
)
locations = st.sidebar.multiselect(
    "Chọn địa điểm",
    options=sorted(df['location_clean'].unique()),
    default=sorted(df['location_clean'].unique())
)
seniorities = st.sidebar.multiselect(
    "Chọn cấp bậc (seniority_level)",
    options=sorted(df['seniority_level'].unique()),
    default=sorted(df['seniority_level'].unique())
)

filtered_df = df[
    df['normalized_role'].isin(roles) &
    df['location_clean'].isin(locations) &
    df['seniority_level'].isin(seniorities)
]

st.markdown(f"**Hiển thị {len(filtered_df)} / {len(df)} job**")

# Layout: 4 cột cho các metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Tổng số job", len(filtered_df))
with col2:
    avg_salary = filtered_df['salary_max'].mean()
    st.metric("Lương trung bình (triệu VND)", f"{avg_salary:.1f}" if pd.notna(avg_salary) else "N/A")
with col3:
    top_role = filtered_df['normalized_role'].value_counts().index[0] if not filtered_df.empty else "N/A"
    st.metric("Vai trò phổ biến nhất", top_role)
with col4:
    top_location = filtered_df['location_clean'].value_counts().index[0] if not filtered_df.empty else "N/A"
    st.metric("Địa điểm phổ biến nhất", top_location)

st.markdown("---")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📈 Lương", "🛠️ Kỹ năng", "📍 Địa điểm & Work mode", "🏷️ Domain Keywords"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        salary_by_role = filtered_df.groupby('normalized_role').agg(
            salary_min_mean=('salary_min', 'mean'),
            salary_max_mean=('salary_max', 'mean')
        ).reset_index()
        salary_by_role = salary_by_role.dropna()
        if not salary_by_role.empty:
            fig = px.bar(
                salary_by_role,
                x='normalized_role',
                y=['salary_min_mean', 'salary_max_mean'],
                title="Lương trung bình theo vai trò",
                labels={'value': 'Triệu VND', 'variable': 'Loại', 'normalized_role': 'Vai trò'},
                barmode='group'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Không có dữ liệu lương cho bộ lọc hiện tại")
    
    with col2:
        salary_by_seniority = filtered_df.groupby('seniority_level').agg(
            salary_max_mean=('salary_max', 'mean')
        ).reset_index().dropna()
        if not salary_by_seniority.empty:
            fig = px.bar(
                salary_by_seniority,
                x='seniority_level',
                y='salary_max_mean',
                title="Lương trung bình theo cấp bậc",
                labels={'salary_max_mean': 'Triệu VND', 'seniority_level': 'Cấp bậc'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Không có dữ liệu lương cho bộ lọc hiện tại")

    if not filtered_df.empty:
        pivot = filtered_df.pivot_table(
            index='normalized_role',
            columns='seniority_level',
            values='salary_max',
            aggfunc='mean'
        )
        if not pivot.empty and pivot.notna().any().any():
            fig = px.imshow(
                pivot,
                text_auto=True,
                aspect="auto",
                title="Lương trung bình (max) theo Role và Seniority"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Không đủ dữ liệu để hiển thị heatmap lương")

with tab2:
    all_skills = []
    for skills in filtered_df['skills']:
        all_skills.extend(skills)
    skill_counts = Counter(all_skills)
    top_skills = skill_counts.most_common(20)
    
    if top_skills:
        skills_df = pd.DataFrame(top_skills, columns=['Skill', 'Count'])
        fig = px.bar(skills_df, x='Count', y='Skill', orientation='h', title="Top 20 kỹ năng phổ biến nhất")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Kỹ năng theo vai trò")
        role_skill = filtered_df.explode('skills').groupby(['normalized_role', 'skills']).size().reset_index(name='count')
        top_role_skills = role_skill.sort_values('count', ascending=False).groupby('normalized_role').head(5)
        st.dataframe(top_role_skills, use_container_width=True)
    else:
        st.info("Không có dữ liệu kỹ năng")

with tab3:
    col1, col2 = st.columns(2)
    with col1:
        location_counts = filtered_df['location_clean'].value_counts().reset_index()
        location_counts.columns = ['location', 'count']
        fig = px.pie(location_counts, names='location', values='count', title="Phân bố job theo địa điểm")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        work_mode_counts = filtered_df['work_mode'].value_counts().reset_index()
        work_mode_counts.columns = ['work_mode', 'count']
        fig = px.bar(work_mode_counts, x='work_mode', y='count', title="Hình thức làm việc")
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    # Domain keywords - đã được xử lý thành list trong load_data
    all_domains = []
    for domains in filtered_df['domain_keywords']:
        if isinstance(domains, list):
            all_domains.extend(domains)
    domain_counts = Counter(all_domains)
    top_domains = domain_counts.most_common(15)
    if top_domains:
        domain_df = pd.DataFrame(top_domains, columns=['Domain', 'Count'])
        fig = px.bar(domain_df, x='Count', y='Domain', orientation='h', title="Top 15 Domain Keywords")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Không có dữ liệu domain keywords")

# Footer
st.markdown("---")
st.caption("Dữ liệu được cập nhật từ TopCV. Báo cáo chất lượng dữ liệu được thực hiện định kỳ.")