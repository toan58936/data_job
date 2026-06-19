markdown
# Hệ thống dữ liệu tuyển dụng ngành Data tại Việt Nam

Hệ thống thu thập, chuẩn hóa và phân tích dữ liệu tuyển dụng các vị trí trong ngành Data (Data Engineer, Data Analyst, Data Scientist, BI, ML/AI) từ nhiều nguồn, nhằm hỗ trợ định hướng nghề nghiệp và phân tích thị trường lao động.

## 🏗️ Kiến trúc tổng thể

Hệ thống được thiết kế theo mô hình **ETL** kết hợp với **Medallion Architecture** (Bronze – Silver – Gold):

- **Bronze Layer**: Dữ liệu thô được crawl từ các trang tuyển dụng (hiện tại: TopCV), lưu dưới dạng JSON.
- **Silver Layer**: Dữ liệu đã được làm sạch, chuẩn hóa, trích xuất kỹ năng, vai trò, mức lương, kinh nghiệm... lưu dưới dạng Parquet.
- **Gold Layer (future)**: Các bảng tổng hợp, báo cáo, dashboard phục vụ phân tích.

Công nghệ sử dụng:
- **Node.js + Playwright** – Tầng thu thập (crawler) với khả năng chống bot.
- **Python + Pandas + PyArrow** – Tầng xử lý và chuẩn hóa.
- **Typer** – CLI tool để điều phối pipeline.
- **Pytest** – Kiểm thử đơn vị và tích hợp.
- **uv** – Quản lý môi trường và dependency.

## 📁 Cấu trúc thư mục
topcv-data-engineer/
├── crawlers/ # Tầng thu thập (Node.js)
│ └── src/
│ ├── topcv-list-crawler.js
│ ├── topcv-detail-crawler.js
│ └── topcv-text-crawler.js
├── transform/ # Tầng xử lý (Python)
│ ├── src/
│ │ ├── main.py
│ │ ├── orchestrator/
│ │ ├── processors/
│ │ ├── schemas/
│ │ ├── io/
│ │ └── utils/
│ └── tests/
│ ├── unit/
│ └── integration/
├── data/
│ ├── bronze/ # Dữ liệu thô JSON (từ crawler)
│ └── silver/ # Dữ liệu chuẩn hóa Parquet
├── logs/ # Log của crawler và transform
├── notebooks/ # Jupyter notebooks cho phân tích
├── cli.py # CLI tool điều phối pipeline
├── run_pipeline.ps1 # Script PowerShell chạy toàn bộ pipeline
└── README.md

text

## 🚀 Hướng dẫn cài đặt và chạy

### Yêu cầu
- **Node.js** (v18+)
- **Python** (v3.10+)
- **uv** (https://docs.astral.sh/uv/)
- **Git**

### 1. Clone dự án
```bash
git clone <repository-url>
cd topcv-data-engineer
2. Cài đặt dependencies
Python (transform + CLI)
bash
uv sync
Node.js (crawler)
bash
cd crawlers
npm install
cd ..
3. Cấu hình (tuỳ chọn)
Các crawler sử dụng cấu hình có sẵn trong file .js. Bạn có thể điều chỉnh headless, delayBetweenJobs, maxRetries... trong từng file.

4. Chạy pipeline
Cách 1: Sử dụng script PowerShell (đơn giản)
powershell
.\run_pipeline.ps1
Cách 2: Sử dụng CLI tool (linh hoạt hơn)
bash
# Xem trợ giúp
uv run python cli.py --help

# Chạy toàn bộ pipeline
uv run python cli.py run

# Chạy riêng từng crawler
uv run python cli.py crawl list
uv run python cli.py crawl detail
uv run python cli.py crawl text
uv run python cli.py crawl all

# Chạy transform
uv run python cli.py transform

# Xem trạng thái dữ liệu
uv run python cli.py status

# Xóa file checkpoint và Silver cũ
uv run python cli.py clean
Cách 3: Chạy thủ công từng bước
bash
# Crawl danh sách job
cd crawlers
node src/topcv-list-crawler.js

# Crawl chi tiết
node src/topcv-detail-crawler.js

# Crawl text
node src/topcv-text-crawler.js
cd ..

# Transform
uv run python -m transform.src.main
🧪 Kiểm thử
Chạy tất cả unit tests:

bash
uv run pytest transform/tests/unit/ -v
Chạy integration test:

bash
uv run pytest transform/tests/integration/ -v
Chạy test cho một processor cụ thể (ví dụ: salary):

bash
uv run pytest transform/tests/unit/test_salary.py -v
📊 Dữ liệu đầu ra
Silver Parquet: data/silver/jobs_silver.parquet

Các trường chính:

job_id, title, company, location_clean

salary_min, salary_max, currency, is_negotiable

exp_min, exp_max, seniority_level

normalized_role (Data Engineer, Data Analyst, ...)

skills (danh sách kỹ năng trích xuất)

domain_keywords (data lake, data warehouse, real-time...)

work_mode, job_work_from_home

📓 Phân tích dữ liệu
Sau khi có Silver, bạn có thể sử dụng Jupyter Notebook để phân tích:

bash
uv add jupyter matplotlib seaborn
uv run jupyter notebook
Mở thư mục notebooks/ và bắt đầu khám phá dữ liệu.

🛠️ Phát triển và mở rộng
Thêm nguồn dữ liệu mới: Tạo crawler riêng cho ITviec, VietnamWorks, LinkedIn… và tích hợp vào pipeline.

Nâng cấp extract skills: Sử dụng NLP (spaCy, NER) để trích xuất kỹ năng chính xác hơn.

Tầng Gold: Tạo các bảng tổng hợp (lương trung bình theo role, top skills, phân bố địa điểm) phục vụ dashboard.

📄 License
MIT

👤 Tác giả
Tên Nguyễn Văn Toàn – Data/ analyst engineer

text
Đây là README đầy đủ, chi tiết và chuyên nghiệp. Bạn có thể điều chỉnh tên tác giả, repository URL, và bổ sung thêm phần giới thiệu về mục tiêu dự án nếu cần.