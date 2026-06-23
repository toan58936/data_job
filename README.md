# Hệ thống dữ liệu tuyển dụng ngành Data tại Việt Nam

Hệ thống thu thập, chuẩn hóa và phân tích dữ liệu tuyển dụng các vị trí trong ngành Data (Data Engineer, Data Analyst, Data Scientist, BI, ML/AI) từ nhiều nguồn, nhằm hỗ trợ định hướng nghề nghiệp và phân tích thị trường lao động.

---

## 🏗️ Kiến trúc tổng thể

Hệ thống được thiết kế theo mô hình **ETL** kết hợp với **Medallion Architecture** (Bronze – Silver – Gold):

- **Bronze Layer**: Dữ liệu thô được crawl từ các trang tuyển dụng (hiện tại: TopCV), lưu dưới dạng JSON.
- **Silver Layer**: Dữ liệu đã được làm sạch, chuẩn hóa, trích xuất kỹ năng, vai trò, mức lương, kinh nghiệm... lưu dưới dạng Parquet.
- **Gold Layer**: Các bảng tổng hợp, báo cáo, dashboard phục vụ phân tích.

**Công nghệ sử dụng**:

- **Node.js + Playwright** – Tầng thu thập (crawler) với khả năng chống bot.
- **Python + Pandas + PyArrow** – Tầng xử lý và chuẩn hóa.
- **Typer** – CLI tool để điều phối pipeline.
- **Pytest** – Kiểm thử đơn vị và tích hợp.
- **Streamlit + Plotly** – Dashboard phân tích.
- **uv** – Quản lý môi trường và dependency.

---

## 📁 Cấu trúc thư mục

```
topcv-data-engineer/
├── crawlers/                   # Tầng thu thập (Node.js)
│   └── src/
│       ├── topcv-list-crawler.js
│       ├── topcv-detail-crawler.js
│       └── topcv-text-crawler.js
├── transform/                  # Tầng xử lý (Python)
│   ├── src/
│   │   ├── main.py             # Entry point
│   │   ├── orchestrator/       # Điều phối pipeline
│   │   ├── processors/         # Các module chuẩn hóa
│   │   ├── schemas/            # Schema dữ liệu
│   │   ├── io/                 # Đọc/ghi dữ liệu
│   │   ├── quality/            # Data Quality
│   │   └── utils/              # Tiện ích
│   └── tests/                  # Unit tests
├── data/
│   ├── bronze/                 # Dữ liệu thô JSON (từ crawler)
│   ├── silver/                 # Dữ liệu chuẩn hóa Parquet
|   ├── gold/                   # dữ liệu insign
│   └── quality/                # Báo cáo chất lượng dữ liệu
├── logs/                       # Log của crawler và transform
├── notebooks/                  # Jupyter notebooks cho phân tích
├── scripts/                    # Script hỗ trợ
├── app.py                      # Dashboard Streamlit
├── cli.py                      # CLI tool điều phối pipeline
├── run_pipeline.ps1            # Script PowerShell chạy toàn bộ pipeline
├── config.yaml                 # Cấu hình pipeline và quality
├── Makefile                    # Makefile cho pipeline
└── README.md
```

---

## 🚀 Hướng dẫn cài đặt và chạy

### Yêu cầu

- **Node.js** (v18+)
- **Python** (v3.12+)
- **uv** (https://docs.astral.sh/uv/)
- **Git**

### 1. Clone dự án

```bash
git clone https://github.com/your-username/topcv-data-engineer.git
cd topcv-data-engineer
```

### 2. Cài đặt dependencies

**Python** (transform + CLI + quality)

```bash
uv sync
```

**Node.js** (crawler)

```bash
cd crawlers
npm install
cd ..
```

### 3. Cấu hình (tùy chọn)

Các crawler sử dụng cấu hình có sẵn trong file `.js`. Bạn có thể điều chỉnh `headless`, `delayBetweenJobs`, `maxRetries`...

Cấu hình pipeline và quality có thể chỉnh sửa trong `config.yaml`:

- Ngưỡng cho completeness (`warning_threshold`, `error_threshold`, `field_overrides`)
- Các stage của Data Quality
- Định dạng báo cáo
- Tự động dừng pipeline khi có lỗi

---

## 🎯 Cách sử dụng

### 🔹 Cách 1: Script PowerShell (Đơn giản nhất)

```powershell
.\run_pipeline.ps1
```

### 🔹 Cách 2: CLI tool (Linh hoạt hơn)

```bash
# Xem trợ giúp
uv run python cli.py --help

# Pipeline đầy đủ với tất cả role
uv run python cli.py run --roles all

# Pipeline với một vài role
uv run python cli.py run --roles data-engineer,data-analyst

# Tắt quality hoặc gold nếu không muốn chạy
uv run python cli.py run --roles all --no-quality --no-gold

# Chạy riêng từng crawler
uv run python cli.py crawl list --roles all # Crawl tất cả role (đọc từ config.yaml)
uv run python cli.py crawl list --roles data-analyst,data-scientist # Crawl một số role cụ thể
uv run python cli.py crawl list --roles all --headed # Crawl với chế độ hiện browser (không headless)
uv run python cli.py crawl detail
uv run python cli.py crawl text
uv run python cli.py crawl all

# Chạy transform
uv run python cli.py transform --format parquet
# hoặc xuất CSV
uv run python cli.py transform --format csv

# Xây dựng Gold Layer từ Silver
uv run python cli.py gold


# Xóa file checkpoint và Silver cũ
uv run python cli.py clean

# Chạy Data Quality
uv run python cli.py quality

# Chạy Data Quality với config tùy chỉnh
uv run python cli.py quality --config config.yaml

# Xem trạng thái dữ liệu
uv run python cli.py status
```
### 🔹 Cách 3: Makefile

```bash
# Chạy toàn bộ pipeline
make all
# hoặc
make run

# Chạy riêng từng phần
make crawl
make transform

# Dọn dẹp
make clean
```

---

## 📊 Data Quality

Hệ thống tự động kiểm tra chất lượng dữ liệu với 5 giai đoạn:

| Giai đoạn    | Mô tả                                                              |
|--------------|--------------------------------------------------------------------|
| Completeness | Kiểm tra tỷ lệ dữ liệu thiếu ở các trường quan trọng              |
| Validity     | Kiểm tra tính hợp lệ (salary_range, exp_range, currency...)        |
| Accuracy     | Kiểm tra tính chính xác (outlier, lương thỏa thuận...)             |
| Uniqueness   | Kiểm tra trùng lặp và nhất quán giữa role và title                 |
| Timeliness   | Kiểm tra tính kịp thời của dữ liệu                                 |

Báo cáo được lưu theo cấu trúc:

```
data/quality/
└── 2026-06-19/
    ├── report_2026-06-19_10-00-00.md
    └── report_2026-06-19_10-00-00.json
```

---

## 🧪 Kiểm thử

Chạy tất cả unit tests:

```bash
uv run pytest transform/tests/unit/ -v
```

Chạy integration test:

```bash
uv run pytest transform/tests/integration/ -v
```

Chạy test cho một module cụ thể (ví dụ: salary):

```bash
uv run pytest transform/tests/unit/test_salary.py -v
```

---

## 📈 Dashboard

Sau khi có dữ liệu Silver, bạn có thể chạy dashboard Streamlit:

```bash
uv add streamlit plotly
uv run streamlit run dashboard/app.py
```

Dashboard cung cấp:

- Phân tích lương theo role và seniority
- Top 20 kỹ năng phổ biến nhất
- Kỹ năng theo từng vai trò
- Phân bố địa điểm và hình thức làm việc
- Domain keywords

---

## 🛠️ Phát triển và mở rộng

- **Thêm nguồn dữ liệu mới**: Tạo crawler riêng cho ITviec, VietnamWorks, LinkedIn...
- **Nâng cấp extract skills**: Sử dụng NLP (spaCy, NER) để trích xuất kỹ năng chính xác hơn.
- **Thêm stage kiểm tra Bronze**: Kiểm tra dữ liệu thô trước khi transform.
- **Tầng Gold**: Tạo các bảng tổng hợp (lương trung bình theo role, top skills, phân bố địa điểm) phục vụ dashboard.

---

## 📄 License

MIT

---

## 👤 Tác giả

Tên bạn –Nguyễn Văn Toàn -Data/Analyst Engineer

