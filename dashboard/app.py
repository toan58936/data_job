# app.py - Dashboard đọc trực tiếp từ Gold Layer
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Data Job Market Dashboard", layout="wide")
st.title("📊 Hệ thống dữ liệu tuyển dụng ngành Data tại Việt Nam")
st.markdown("---")

# ============================
# 1. ĐỊNH NGHĨA ĐƯỜNG DẪN
# ============================
GOLD_DIR = Path("data/gold")
SILVER_DIR = Path("data/silver")


# ============================
# 2. HÀM TẢI DỮ LIỆU GOLD (CÓ MAPPING RÕ RÀNG)
# ============================
@st.cache_data
def load_gold():
    """Tải toàn bộ các bảng Gold từ thư mục data/gold/."""
    data = {}
    mapping = {
        'metrics.parquet': 'metrics',
        'salary_by_role.parquet': 'salary_by_role',
        'salary_by_seniority.parquet': 'salary_by_seniority',
        'heatmap_salary.parquet': 'heatmap',
        'top_skills.parquet': 'top_skills',
        'skills_by_role.parquet': 'skills_by_role',
        'location_distribution.parquet': 'location_dist',
        'work_mode_distribution.parquet': 'work_mode',
        'top_domains.parquet': 'top_domains'
    }
    for file, key in mapping.items():
        path = GOLD_DIR / file
        if path.exists():
            data[key] = pd.read_parquet(path)
        else:
            data[key] = pd.DataFrame()  # DataFrame rỗng để tránh lỗi None
    return data


@st.cache_data
def load_silver_for_filters():
    """Tải Silver chỉ để lấy danh sách giá trị cho bộ lọc."""
    df = pd.read_parquet(SILVER_DIR / 'jobs_silver.parquet')
    return df


# ============================
# 3. HÀM HỖ TRỢ
# ============================
def safe_unique_values(series):
    """Lấy các giá trị unique khác null và chuyển về string để sorted."""
    vals = [str(x) for x in series.unique() if pd.notna(x)]
    return sorted(vals)


# ============================
# 4. TẢI DỮ LIỆU
# ============================
data = load_gold()
df_silver = load_silver_for_filters()

# ============================
# 5. SIDEBAR - BỘ LỌC
# ============================
st.sidebar.header("Bộ lọc")

roles = st.sidebar.multiselect(
    "Chọn vai trò (normalized_role)",
    options=safe_unique_values(df_silver['normalized_role']),
    default=safe_unique_values(df_silver['normalized_role'])
)
locations = st.sidebar.multiselect(
    "Chọn địa điểm",
    options=safe_unique_values(df_silver['location_clean']),
    default=safe_unique_values(df_silver['location_clean'])
)
seniorities = st.sidebar.multiselect(
    "Chọn cấp bậc (seniority_level)",
    options=safe_unique_values(df_silver['seniority_level']),
    default=safe_unique_values(df_silver['seniority_level'])
)

# Áp dụng bộ lọc lên dữ liệu Silver để đếm số lượng job
filtered_df = df_silver[
    df_silver['normalized_role'].astype(str).isin(roles) &
    df_silver['location_clean'].astype(str).isin(locations) &
    df_silver['seniority_level'].astype(str).isin(seniorities)
]

st.markdown(f"**Hiển thị {len(filtered_df)} / {len(df_silver)} job**")

# ============================
# 6. METRICS
# ============================
metrics = data.get('metrics')
if not metrics.empty:
    m = metrics.iloc[0]
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Tổng số job", m.get('total_jobs', 0))
    with col2:
        avg_salary = m.get('avg_salary_max')
        st.metric("Lương trung bình (triệu VND)", f"{avg_salary:.1f}" if pd.notna(avg_salary) else "N/A")
    with col3:
        st.metric("Vai trò phổ biến nhất", m.get('top_role', "N/A"))
    with col4:
        st.metric("Địa điểm phổ biến nhất", m.get('top_location', "N/A"))
else:
    st.warning("Không có dữ liệu metrics. Vui lòng chạy gold_builder.")

st.markdown("---")

# ============================
# 7. TABS
# ============================
tab1, tab2, tab3, tab4 = st.tabs(["📈 Lương", "🛠️ Kỹ năng", "📍 Địa điểm & Work mode", "🏷️ Domain Keywords"])


# ---------------------------
# TAB 1: LƯƠNG
# ---------------------------
with tab1:
    col1, col2 = st.columns(2)

    with col1:
        salary_by_role = data.get('salary_by_role')
        if not salary_by_role.empty:
            fig = px.bar(
                salary_by_role,
                x='normalized_role',
                y=['salary_min_mean', 'salary_max_mean'],
                title="Lương trung bình theo vai trò",
                labels={'value': 'Triệu VND', 'variable': 'Loại', 'normalized_role': 'Vai trò'},
                barmode='group'
            )
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Không có dữ liệu lương theo role")

    with col2:
        salary_by_seniority = data.get('salary_by_seniority')
        if not salary_by_seniority.empty:
            fig = px.bar(
                salary_by_seniority,
                x='seniority_level',
                y='salary_max_mean',
                title="Lương trung bình theo cấp bậc",
                labels={'salary_max_mean': 'Triệu VND', 'seniority_level': 'Cấp bậc'}
            )
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Không có dữ liệu lương theo seniority")

    # Heatmap
    heatmap = data.get('heatmap')
    if heatmap is not None and not heatmap.empty:
        try:
            pivot_heatmap = heatmap.pivot(index='normalized_role', columns='seniority_level', values='salary_max_mean')
            if not pivot_heatmap.empty:
                fig = px.imshow(
                    pivot_heatmap,
                    text_auto=True,
                    aspect="auto",
                    title="Lương trung bình (max) theo Role và Seniority"
                )
                st.plotly_chart(fig, width='stretch')
            else:
                st.info("Không đủ dữ liệu heatmap")
        except Exception as e:
            st.info(f"Không thể tạo heatmap: {e}")
    else:
        st.info("Không có dữ liệu heatmap")


# ---------------------------
# TAB 2: KỸ NĂNG
# ---------------------------
with tab2:
    top_skills = data.get('top_skills')
    if top_skills is not None and not top_skills.empty:
        fig = px.bar(
            top_skills,
            x='count',
            y='skill',
            orientation='h',
            title="Top 20 kỹ năng phổ biến nhất"
        )
        st.plotly_chart(fig, width='stretch')

        st.subheader("Kỹ năng theo vai trò")
        skills_by_role = data.get('skills_by_role')
        if skills_by_role is not None and not skills_by_role.empty:
            st.dataframe(skills_by_role, use_container_width=True)
        else:
            st.info("Không có dữ liệu kỹ năng theo role")
    else:
        st.info("Không có dữ liệu kỹ năng")


# ---------------------------
# TAB 3: ĐỊA ĐIỂM & WORK MODE
# ---------------------------
with tab3:
    col1, col2 = st.columns(2)

    with col1:
        location_dist = data.get('location_dist')
        if location_dist is not None and not location_dist.empty:
            fig = px.pie(
                location_dist,
                names='location',
                values='count',
                title="Phân bố job theo địa điểm"
            )
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Không có dữ liệu địa điểm")

    with col2:
        work_mode = data.get('work_mode')
        if work_mode is not None and not work_mode.empty:
            fig = px.bar(
                work_mode,
                x='work_mode',
                y='count',
                title="Hình thức làm việc"
            )
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Không có dữ liệu work mode")


# ---------------------------
# TAB 4: DOMAIN KEYWORDS
# ---------------------------
with tab4:
    top_domains = data.get('top_domains')
    if top_domains is not None and not top_domains.empty:
        fig = px.bar(
            top_domains,
            x='count',
            y='domain',
            orientation='h',
            title="Top 15 Domain Keywords"
        )
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("Không có dữ liệu domain keywords")


# ============================
# 8. FOOTER
# ============================
st.markdown("---")
st.caption("Dữ liệu được cập nhật từ Gold Layer. Gold được xây dựng từ Silver và cập nhật định kỳ.")