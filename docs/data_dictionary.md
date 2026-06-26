# Data Dictionary - Hệ thống Dữ liệu Tuyển dụng Ngành Data

**Phiên bản:** 1.0  
**Ngày cập nhật:** 23/06/2026  
**Tác giả:** Nguyễn Văn Toàn  

---

## 1. Giới thiệu

Tài liệu này mô tả chi tiết các trường dữ liệu (schema) được sử dụng trong toàn bộ hệ thống, từ khi thu thập thô (Bronze) đến khi làm sạch (Silver) và tổng hợp (Gold). Mục tiêu là cung cấp một nguồn tham chiếu duy nhất cho các nhà phát triển và phân tích dữ liệu.

Hệ thống sử dụng kiến trúc **Medallion**:
- **Bronze (Đồng)**: Dữ liệu thô, dạng JSON, lưu đúng như những gì crawl được từ website.
- **Silver (Bạc)**: Dữ liệu đã được làm sạch, chuẩn hóa và tích hợp, lưu dưới dạng Parquet.
- **Gold (Vàng)**: Dữ liệu tổng hợp (aggregated) phục vụ trực tiếp cho Dashboard và báo cáo.

---

## 2. Tầng Bronze (Raw JSON)

Dữ liệu thô được crawl từ các nguồn (TopCV, ITviec...) và được lưu thành các file JSON trong thư mục `data/bronze/`.

### 2.1. `jobs_all.json`
Danh sách job cơ bản từ các trang tìm kiếm.

| Tên trường | Kiểu dữ liệu | Mô tả |
| :--- | :--- | :--- |
| `title` | string | Tiêu đề công việc (gốc). |
| `company` | string | Tên công ty tuyển dụng. |
| `location` | string | Địa điểm làm việc (thô). |
| `salary` | string | Mô tả mức lương (thô). |
| `experience` | string | Yêu cầu kinh nghiệm (thô). |
| `url` | string | Đường dẫn đến trang chi tiết (có tham số tracking). |

### 2.2. `jobs_detail.json`
Thông tin chi tiết của từng job.

| Tên trường | Kiểu dữ liệu | Mô tả |
| :--- | :--- | :--- |
| `id` | string | Mã định danh job (số trên URL). |
| `url` | string | Đường dẫn đầy đủ. |
| `normalized_url` | string | URL đã loại bỏ tham số tracking (dùng làm khóa). |
| `title` | string | Tiêu đề chi tiết. |
| `company` | string | Tên công ty. |
| `salary` | string | Mức lương (thô). |
| `location` | string | Địa điểm. |
| `experience` | string | Kinh nghiệm (thô). |
| `deadline` | string | Hạn nộp hồ sơ (đã chuẩn hóa YYYY-MM-DD). |
| `level` | string | Cấp bậc (Nhân viên, Trưởng nhóm...). |
| `number_of_hires` | int | Số lượng tuyển dụng. |
| `job_type` | string | Loại hình (Toàn thời gian, Bán thời gian...). |
| `working_time` | string | Thời gian làm việc (mô tả). |
| `location_detail` | string | Địa chỉ chi tiết. |
| `crawled_at` | datetime | Thời điểm crawl (ISO 8601). |

### 2.3. `job_text_final.json`
Mô tả công việc và yêu cầu.

| Tên trường | Kiểu dữ liệu | Mô tả |
| :--- | :--- | :--- |
| `id` | string | Mã định danh job. |
| `url` | string | Đường dẫn đầy đủ. |
| `normalized_url` | string | URL chuẩn. |
| `title` | string | Tiêu đề. |
| `description` | text | Mô tả công việc. |
| `requirements` | text | Yêu cầu ứng viên. |
| `benefits` | text | Quyền lợi được hưởng. |
| `crawled_at` | datetime | Thời điểm crawl. |

---

## 3. Tầng Silver (Normalized Data)

Dữ liệu được chuẩn hóa và hợp nhất thành file Parquet `data/silver/jobs_silver.parquet`. Đây là bảng dữ liệu chính dùng để phân tích.

| # | Tên trường | Kiểu dữ liệu | Mô tả | Nguồn xử lý |
| :---: | :--- | :--- | :--- | :--- |
| 1 | `job_id` | string | Mã định danh job (từ URL). | Reader |
| 2 | `source` | string | Nguồn dữ liệu (`TopCV`, `ITviec`...). | Reader |
| 3 | `job_url` | string | Đường dẫn job. | Reader |
| 4 | `title` | string | Tiêu đề gốc. | Reader |
| 5 | `company` | string | Tên công ty. | Reader |
| 6 | `location_raw` | string | Địa điểm thô. | Reader |
| 7 | `location_clean` | string | Địa điểm chuẩn hóa (Hà Nội, Hồ Chí Minh...). | `location.py` |
| 8 | `salary_min` | float | Mức lương tối thiểu (triệu VND). | `salary.py` |
| 9 | `salary_max` | float | Mức lương tối đa (triệu VND). | `salary.py` |
| 10 | `currency` | string | Đơn vị tiền tệ (`VND`). | `salary.py` |
| 11 | `is_negotiable` | bool | Có phải lương thỏa thuận không. | `salary.py` |
| 12 | `exp_min` | float | Kinh nghiệm tối thiểu (năm). | `experience.py` |
| 13 | `exp_max` | float | Kinh nghiệm tối đa (năm). | `experience.py` |
| 14 | `deadline` | date | Hạn nộp hồ sơ. | Reader |
| 15 | `level` | string | Cấp bậc. | Reader |
| 16 | `number_of_hires` | int | Số lượng tuyển. | Reader |
| 17 | `job_schedule_type` | string | Loại hợp đồng (`Full-time`, `Part-time`). | Mapping |
| 18 | `working_time` | string | Thời gian làm việc mô tả. | Reader |
| 19 | `job_country` | string | Quốc gia (`Vietnam`). | Hardcode |
| 20 | `work_mode` | string | Hình thức làm việc (`Onsite`, `Hybrid`, `Remote`). | `work_mode.py` |
| 21 | `job_work_from_home` | bool | Cho phép làm việc từ xa không. | `work_mode.py` |
| 22 | `seniority_level` | string | Cấp bậc chuẩn hóa (`Junior`, `Middle`, `Senior`, `Lead`). | `seniority.py` |
| 23 | `normalized_role` | string | Vai trò chuẩn hóa (`Data Engineer`, `Data Analyst`...). | `role.py` |
| 24 | `skills` | list[String] | Danh sách kỹ năng (ví dụ: `['python', 'sql']`). | `skills.py` |
| 25 | `domain_keywords` | list[String] | Lĩnh vực/từ khóa ngành (ví dụ: `['fintech']`). | `domain.py` |
| 26 | `description` | text | Mô tả công việc (chuẩn hóa). | Reader |
| 27 | `requirements` | text | Yêu cầu ứng viên (chuẩn hóa). | Reader |
| 28 | `benefits` | text | Quyền lợi (chuẩn hóa). | Reader |
| 29 | `crawled_at` | datetime | Thời điểm crawl (UTC). | Reader |

---

## 4. Tầng Gold (Aggregated Tables)

Các bảng tổng hợp được tạo bởi `gold_builder.py` và lưu trong `data/gold/`. Phục vụ trực tiếp cho Dashboard.

### 4.1. `metrics.parquet`
Thống kê tổng quan.

| Tên trường | Kiểu | Mô tả |
| :--- | :--- | :--- |
| `total_jobs` | int | Tổng số job. |
| `avg_salary_max` | float | Lương trung bình (max). |
| `top_role` | string | Vai trò phổ biến nhất. |
| `top_location` | string | Địa điểm phổ biến nhất. |

### 4.2. `salary_by_role.parquet`
Lương theo role.

| Tên trường | Kiểu | Mô tả |
| :--- | :--- | :--- |
| `normalized_role` | string | Vai trò. |
| `salary_min_mean` | float | Lương min trung bình. |
| `salary_max_mean` | float | Lương max trung bình. |

### 4.3. `salary_by_seniority.parquet`
Lương theo cấp bậc.

| Tên trường | Kiểu | Mô tả |
| :--- | :--- | :--- |
| `seniority_level` | string | Cấp bậc. |
| `salary_max_mean` | float | Lương max trung bình. |

### 4.4. `heatmap_salary.parquet`
Heatmap lương (Long format).

| Tên trường | Kiểu | Mô tả |
| :--- | :--- | :--- |
| `normalized_role` | string | Vai trò. |
| `seniority_level` | string | Cấp bậc. |
| `salary_max_mean` | float | Lương max trung bình. |

### 4.5. `top_skills.parquet`
Top 20 kỹ năng phổ biến.

| Tên trường | Kiểu | Mô tả |
| :--- | :--- | :--- |
| `skill` | string | Tên kỹ năng. |
| `count` | int | Số lần xuất hiện. |

### 4.6. `skills_by_role.parquet`
Top 5 kỹ năng theo từng role.

| Tên trường | Kiểu | Mô tả |
| :--- | :--- | :--- |
| `normalized_role` | string | Vai trò. |
| `skill` | string | Tên kỹ năng. |
| `count` | int | Số lần xuất hiện. |

### 4.7. `location_distribution.parquet`
Phân bố job theo địa điểm.

| Tên trường | Kiểu | Mô tả |
| :--- | :--- | :--- |
| `location` | string | Địa điểm (clean). |
| `count` | int | Số lượng job. |

### 4.8. `work_mode_distribution.parquet`
Phân bố hình thức làm việc.

| Tên trường | Kiểu | Mô tả |
| :--- | :--- | :--- |
| `work_mode` | string | Hình thức. |
| `count` | int | Số lượng job. |

### 4.9. `top_domains.parquet`
Top 15 Domain Keywords.

| Tên trường | Kiểu | Mô tả |
| :--- | :--- | :--- |
| `domain` | string | Tên domain. |
| `count` | int | Số lần xuất hiện. |

---

## 5. Quy ước và Ghi chú

- **Null / None**: Các trường không có dữ liệu được để là `None` (hoặc `NaN` trong Pandas), không sử dụng giá trị mặc định gây nhiễu (ví dụ: `"Unknown"`).
- **Thời gian (Crawled At)**: Lưu ở định dạng UTC (ISO 8601) để chuẩn hóa múi giờ.
- **Tiền tệ**: Tất cả lương đều được quy đổi về đơn vị **triệu VND** (float).
- **Kỹ năng**: Được trích xuất từ văn bản và lưu dưới dạng danh sách chuỗi, không phân biệt chữ hoa chữ thường.
- **Role**: Nếu không thể xác định `normalized_role`, giá trị sẽ là `None`.