# 🇻🇳 Hệ thống dữ liệu tuyển dụng ngành Data tại Việt Nam

> Thu thập, chuẩn hóa và phân tích thị trường tuyển dụng ngành Data từ TopCV theo kiến trúc Medallion (Bronze → Silver → Gold).

---

## Mục lục

- [Tổng quan](#tổng-quan)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
- [Cài đặt](#cài-đặt)
- [Cấu hình](#cấu-hình)
- [Hướng dẫn sử dụng CLI](#hướng-dẫn-sử-dụng-cli)
- [Chi tiết từng tầng](#chi-tiết-từng-tầng)
  - [Tầng Bronze — Crawling](#tầng-bronze--crawling)
  - [Tầng Silver — Transform](#tầng-silver--transform)
  - [Data Quality](#data-quality)
  - [Tầng Gold — Aggregation](#tầng-gold--aggregation)
  - [Dashboard](#dashboard)
- [Schema dữ liệu](#schema-dữ-liệu)
- [Chạy Tests](#chạy-tests)
- [Lộ trình phát triển](#lộ-trình-phát-triển)

---

## Tổng quan

Project này xây dựng một data pipeline hoàn chỉnh để trả lời câu hỏi thực tế của người học Data:

- Thị trường đang cần kỹ năng gì? (SQL, Python, Spark, dbt, Airflow...)
- Mức lương phổ biến theo role và seniority là bao nhiêu?
- Vị trí nào phù hợp với Fresher, Junior, Senior?
- Tỷ lệ Remote / Hybrid / Onsite đang như thế nào?

**Nguồn dữ liệu hiện tại:** [TopCV.vn](https://www.topcv.vn)

**Roles được theo dõi:** Data Engineer · Data Analyst · Data Scientist · Business Intelligence

---

## Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────────┐
│                        CRAWLING (Node.js)                       │
│   list-crawler-multi.js → detail-crawler.js → text-crawler.js  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BRONZE LAYER  (data/bronze/)                 │
│        jobs_all.json · jobs_detail.json · job_text_final.json   │
│                    + checkpoint files                           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│               SILVER TRANSFORM  (Python / Pandas)               │
│                                                                 │
│  reader.py (merge 3 files)                                      │
│       ↓                                                         │
│  8 Processors:                                                  │
│    salary · experience · location · skills · domain             │
│    role · seniority · work_mode                                 │
│       ↓                                                         │
│  SilverJob dataclass → jobs_silver.parquet                      │
└───────────┬─────────────────────────┬───────────────────────────┘
            │                         │
            ▼                         ▼
┌───────────────────┐     ┌───────────────────────────────────────┐
│   DATA QUALITY    │     │         GOLD LAYER  (data/gold/)      │
│                   │     │                                       │
│  5 dimensions:    │     │  metrics.parquet                      │
│  · completeness   │     │  salary_by_role.parquet               │
│  · validity       │     │  salary_by_seniority.parquet          │
│  · accuracy       │     │  heatmap_salary.parquet               │
│  · uniqueness     │     │  top_skills.parquet                   │
│  · timeliness     │     │  skills_by_role.parquet               │
│                   │     │  location_distribution.parquet        │
│  → MD + JSON      │     │  work_mode_distribution.parquet       │
│    reports        │     │  top_domains.parquet                  │
└───────────────────┘     └────────────────┬──────────────────────┘
                                           │
                                           ▼
                          ┌────────────────────────────────────────┐
                          │     DASHBOARD  (Streamlit + Plotly)    │
                          │     Đọc từ Gold Layer                  │
                          └────────────────────────────────────────┘
```

---

## Cấu trúc thư mục

```
data_job/
├── cli.py                          # Entry point — Typer CLI
├── config.yaml                     # Cấu hình toàn hệ thống
├── pyproject.toml                  # Python dependencies (uv)
├── makefile                        # Shortcuts cho các lệnh phổ biến
│
├── crawlers/                       # Node.js crawlers
│   ├── package.json
│   └── src/
│       ├── list-crawler-multi.js   # Crawler danh sách (multi-role)
│       ├── topcv-detail-crawler.js # Crawler chi tiết từng job
│       └── topcv-text-crawler.js   # Crawler mô tả công việc (full text)
│
├── transform/                      # Python transform package
│   └── src/
│       ├── orchestrator/
│       │   └── pipeline.py         # Điều phối toàn bộ Bronze → Silver
│       ├── io/
│       │   ├── reader.py           # Merge 3 file Bronze
│       │   └── writer.py           # Ghi Silver Parquet / CSV
│       ├── processors/             # 8 processors độc lập
│       │   ├── salary.py           # Parse lương (VND / USD / Thoả thuận)
│       │   ├── experience.py       # Parse số năm kinh nghiệm
│       │   ├── location.py         # Chuẩn hóa địa điểm
│       │   ├── skills.py           # Trích xuất kỹ năng bằng regex
│       │   ├── domain.py           # Trích xuất domain keywords
│       │   ├── role.py             # Chuẩn hóa role (Data Engineer, ...)
│       │   ├── seniority.py        # Phân loại Junior / Middle / Senior
│       │   └── work_mode.py        # Onsite / Hybrid / Remote
│       ├── schemas/
│       │   └── silver_schema.py    # SilverJob dataclass với from_dict / to_dict
│       ├── gold/
│       │   └── gold_builder.py     # Xây dựng 9 bảng Gold từ Silver
│       ├── quality/                # Data Quality framework
│       │   ├── runner.py           # Orchestrator — chạy 5 stages
│       │   ├── completeness.py
│       │   ├── validity.py
│       │   ├── accuracy.py
│       │   ├── uniqueness.py
│       │   ├── timeliness.py
│       │   └── reporter.py         # Xuất report MD + JSON
│       └── utils/
│           ├── config.py           # Constants, mappings, keyword lists
│           └── config_loader.py    # Đọc config.yaml với fallback
│   └── tests/
│       ├── conftest.py
│       ├── fixtures/               # Sample JSON data cho test
│       ├── unit/                   # Unit test từng processor + quality stage
│       └── integration/            # Integration test toàn bộ pipeline flow
│
├── dashboard/
│   └── app.py                      # Streamlit dashboard đọc từ Gold
│
├── data/
│   ├── bronze/                     # Raw JSON (gitignored)
│   ├── silver/                     # Parquet sau transform (gitignored)
│   ├── gold/                       # Pre-aggregated Parquet (9 tables)
│   └── quality/                    # Quality reports MD + JSON (gitignored)
│
└── notebooks/
    ├── analyze_skills_frequency.ipynb
    └── eda2.ipynb
```

---

## Yêu cầu hệ thống

| Công nghệ | Phiên bản tối thiểu | Dùng để |
|-----------|--------------------|----|
| Python | 3.12+ | Transform, quality, gold, dashboard |
| Node.js | 20+ | Crawlers Playwright |
| uv | latest | Quản lý Python environment |
| npm | 9+ | Quản lý Node.js dependencies |

---

## Cài đặt

### 1. Clone repo

```bash
git clone https://github.com/toan58936/data_job.git
cd data_job
```

### 2. Cài đặt Python dependencies

```bash
# Cài uv nếu chưa có
curl -LsSf https://astral.sh/uv/install.sh | sh

# Cài Python environment
uv sync
```

### 3. Cài đặt Node.js dependencies cho crawler

```bash
cd crawlers
npm install
cd ..
```

### 4. Cài đặt Playwright browsers

```bash
uv run npx playwright install chromium
```

---

## Cấu hình

Toàn bộ cấu hình nằm trong `config.yaml`:

```yaml
pipeline:
  bronze_dir: "data/bronze"
  silver_dir: "data/silver"
  gold_dir:   "data/gold"
  output_format: "parquet"

gold:
  enabled: true
  output_dir: "data/gold"

quality:
  completeness:
    warning_threshold: 0.95   # Cảnh báo khi completeness < 95%
    error_threshold: 0.80     # Lỗi khi completeness < 80%
    field_overrides:
      salary_min: 0.25        # Salary cho phép null rate cao hơn (thỏa thuận)
      salary_max: 0.25
  validity:
    warning_threshold: 5      # Cảnh báo khi > 5% records có lỗi validity
    error_threshold: 15
  enabled_stages:
    - completeness
    - validity
    - accuracy
    - uniqueness
    - timeliness
  report_formats: [markdown, json]
  report_dir: "data/quality"
  stop_on_error: true         # Dừng pipeline nếu quality check thất bại

crawler:
  roles:
    - data-engineer
    - data-analyst
    - data-scientist
    - business-intelligence
    # Thêm role mới tại đây:
    # - machine-learning
    # - ai-engineer
    # - analytics-engineer
```

---

## Hướng dẫn sử dụng CLI

Toàn bộ pipeline được điều phối qua `cli.py` với Typer. Cú pháp:

```bash
uv run python cli.py [COMMAND] [OPTIONS]
```

### Xem trạng thái hiện tại

```bash
uv run python cli.py status
```

Hiển thị trạng thái các file Bronze, Silver và số records đang có.

---

### Chạy toàn bộ pipeline (khuyến nghị)

```bash
# Chạy đầy đủ: crawl → transform → quality → gold
uv run python cli.py run

# Chạy với browser hiển thị (debug crawl)
uv run python cli.py run --headed

# Chạy chỉ một số role cụ thể
uv run python cli.py run --roles "data-engineer,data-analyst"

# Bỏ qua Gold layer
uv run python cli.py run --no-gold

# Bỏ qua Data Quality checks
uv run python cli.py run --no-quality
```

---

### Crawl dữ liệu (từng bước)

```bash
# Crawl tất cả (list → detail → text)
uv run python cli.py crawl all

# Chỉ crawl danh sách job (bước 1)
uv run python cli.py crawl list

# Chỉ crawl chi tiết job (bước 2, cần có jobs_all.json)
uv run python cli.py crawl detail

# Chỉ crawl full text mô tả (bước 3, cần có jobs_detail.json)
uv run python cli.py crawl text

# Crawl headless / headed
uv run python cli.py crawl all --headless   # mặc định
uv run python cli.py crawl all --headed     # hiện browser

# Crawl chỉ một số role
uv run python cli.py crawl list --roles "data-engineer,data-scientist"
```

**Lưu ý:** Crawler có checkpoint — nếu bị ngắt giữa chừng, lần chạy tiếp theo sẽ tiếp tục từ điểm dừng, không crawl lại từ đầu.

---

### Transform Bronze → Silver

```bash
# Transform với output mặc định (Parquet)
uv run python cli.py transform

# Output ra CSV
uv run python cli.py transform --format csv

# Bỏ qua Gold hoặc Quality
uv run python cli.py transform --no-gold
uv run python cli.py transform --no-quality
```

---

### Xây dựng Gold Layer

```bash
# Xây Gold từ Silver mặc định
uv run python cli.py gold

# Chỉ định đường dẫn tùy chỉnh
uv run python cli.py gold --silver-file data/silver/jobs_silver.parquet \
                          --output-dir data/gold
```

---

### Chạy Data Quality độc lập

```bash
# Chạy toàn bộ 5 stages
uv run python cli.py quality

# Chỉ chạy một số stage cụ thể
uv run python cli.py quality --stages "completeness,validity"

# Silent mode (không in ra console)
uv run python cli.py quality --silent
```

Report được lưu tại `data/quality/<ngày>/report.md` và `report.json`.

---

### Dọn dẹp

```bash
uv run python cli.py clean
```

Xóa checkpoint files và Silver Parquet cũ.

---

### Makefile shortcuts

```bash
make run       # uv run python cli.py run (toàn bộ pipeline)
make crawl     # Crawl 3 bước thủ công qua node
make transform # Transform với format parquet
make clean     # Xóa Silver + checkpoints
```

---

## Chi tiết từng tầng

### Tầng Bronze — Crawling

Crawler viết bằng Node.js với Playwright + Stealth plugin để tránh bị detect.

**Quy trình 3 bước:**

| Bước | Script | Input | Output |
|------|--------|-------|--------|
| 1. List | `list-crawler-multi.js` | Danh sách roles từ `config.yaml` | `data/bronze/jobs_all.json` |
| 2. Detail | `topcv-detail-crawler.js` | `jobs_all.json` | `data/bronze/jobs_detail.json` |
| 3. Text | `topcv-text-crawler.js` | `jobs_detail.json` | `data/bronze/job_text_final.json` |

**Tính năng:**
- **Multi-role trong một lần chạy** — `list-crawler-multi.js` crawl song song nhiều role từ config
- **Checkpoint-based resume** — mỗi lần crawl ghi checkpoint, nếu bị ngắt sẽ tiếp tục từ điểm dừng
- **URL deduplication** — hash URL để không crawl lại bản ghi đã có
- **Stealth mode** — dùng `puppeteer-extra-plugin-stealth` để giảm khả năng bị block

---

### Tầng Silver — Transform

**File:** `transform/src/orchestrator/pipeline.py`

Pipeline đọc 3 file Bronze, merge theo URL, áp dụng 8 processors trên từng record, xuất ra `SilverJob` dataclass.

#### 8 Processors

| Processor | Logic |
|-----------|-------|
| `salary.py` | Parse lương dạng "27 - 45 triệu", "Tới 22 triệu", "800 - 3,500 USD", "Thoả thuận" → `salary_min`, `salary_max`, `currency`, `is_negotiable` |
| `experience.py` | Parse "2 - 5 năm", "Không yêu cầu", "Trên 3 năm" → `exp_min`, `exp_max` (số nguyên) |
| `location.py` | Map địa điểm về các tỉnh/thành chuẩn: Hà Nội, Hồ Chí Minh, Đà Nẵng... |
| `role.py` | Chuẩn hóa title thành role: Data Engineer · Data Analyst · Data Scientist · BI Analyst · ML Engineer · AI Engineer · Analytics Engineer |
| `seniority.py` | Phân loại Junior / Middle / Senior / Lead từ title và `exp_min` |
| `skills.py` | Trích xuất kỹ năng từ title + description + requirements bằng regex boundary-aware (xử lý đúng `c++`, `c#`, `power bi`) |
| `domain.py` | Trích xuất domain keywords (fintech, e-commerce, logistics...) |
| `work_mode.py` | Phân loại Onsite / Hybrid / Remote từ `working_time` và mô tả |

#### SilverJob Schema

```
job_id          source          job_url         title
company         location_raw    location_clean  salary_min
salary_max      currency        is_negotiable   exp_min
exp_max         deadline        level           number_of_hires
job_schedule_type  working_time  job_country    work_mode
job_work_from_home  seniority_level  normalized_role
skills (List)   domain_keywords (List)          description
requirements    benefits        crawled_at
```

---

### Data Quality

**Framework 5 chiều**, chạy tự động sau mỗi lần transform (có thể tắt bằng `--no-quality`).

| Stage | Kiểm tra |
|-------|---------|
| **Completeness** | Tỷ lệ non-null của các trường quan trọng (`title`, `company`, `normalized_role`...) so với ngưỡng warning/error trong config |
| **Validity** | Ràng buộc logic: `salary_min <= salary_max`, `exp_min <= exp_max`, `salary_max > 0`, URL hợp lệ |
| **Accuracy** | Phát hiện outlier lương, kiểm tra role hợp lệ nằm trong whitelist |
| **Uniqueness** | Tỷ lệ trùng lặp URL, nhất quán giữa `title` và `normalized_role` |
| **Timeliness** | Tỷ lệ records được crawl trong N ngày gần nhất |

**Output:** Report Markdown + JSON tại `data/quality/<YYYY-MM-DD>/`

**Behavior:**
- Exit code `0` = PASS
- Exit code `1` = WARNING (vượt ngưỡng cảnh báo)
- Exit code `2` = ERROR (vượt ngưỡng lỗi)
- Khi `stop_on_error: true` trong config → pipeline dừng nếu có ERROR

---

### Tầng Gold — Aggregation

**File:** `transform/src/gold/gold_builder.py`

Đọc Silver Parquet và pre-compute 9 bảng insight, lưu tại `data/gold/`.

| File Parquet | Nội dung |
|-------------|---------|
| `metrics.parquet` | Tổng số job, avg salary, top role, top location |
| `salary_by_role.parquet` | Lương trung bình (min/max mean) theo `normalized_role` |
| `salary_by_seniority.parquet` | Lương trung bình theo `seniority_level` |
| `heatmap_salary.parquet` | Lương max mean theo Role × Seniority (long format) |
| `top_skills.parquet` | Top 20 kỹ năng phổ biến nhất (skill + count) |
| `skills_by_role.parquet` | Top 5 kỹ năng theo từng role |
| `location_distribution.parquet` | Số lượng job theo địa điểm |
| `work_mode_distribution.parquet` | Phân bổ Onsite / Hybrid / Remote |
| `top_domains.parquet` | Top 15 domain keywords (fintech, e-commerce...) |

---

### Dashboard

**File:** `dashboard/app.py`

```bash
uv run streamlit run dashboard/app.py
```

Mở trình duyệt tại `http://localhost:8501`

Dashboard đọc từ **Gold Layer** (`data/gold/`) — không tính toán trực tiếp trên Silver.

**Tính năng:**
- Bộ lọc theo Role, Location, Seniority, Work Mode
- Biểu đồ phân bổ lương theo role và seniority
- Heatmap lương: Role × Seniority
- Top kỹ năng được yêu cầu (bar chart)
- Kỹ năng theo từng role
- Phân bổ địa điểm và hình thức làm việc
- Bảng jobs raw (Silver) để drill-down

---

## Schema dữ liệu

### Bronze (raw JSON)

```json
{
  "id": "12345",
  "url": "https://www.topcv.vn/viec-lam/...",
  "normalized_url": "https://www.topcv.vn/viec-lam/...",
  "title": "Senior Data Engineer",
  "company": "ABC Technology",
  "location": "Hà Nội",
  "salary": "27 - 45 triệu",
  "experience": "3 - 5 năm",
  "description": "...",
  "requirements": "...",
  "benefits": "...",
  "source": "TopCV",
  "crawled_at": "2026-06-23T10:00:00"
}
```

### Silver (Parquet)

Xem đầy đủ tại `transform/src/schemas/silver_schema.py` — `SilverJob` dataclass với 29 trường.

### Gold (Parquet)

9 bảng pre-aggregated, mô tả chi tiết tại mục [Tầng Gold](#tầng-gold--aggregation).

---

## Chạy Tests

```bash
# Toàn bộ test suite
uv run pytest

# Chỉ unit tests
uv run pytest transform/tests/unit/ -v

# Chỉ integration tests
uv run pytest transform/tests/integration/ -v

# Một processor cụ thể
uv run pytest transform/tests/unit/test_salary.py -v

# Toàn bộ quality tests
uv run pytest transform/tests/unit/test_quality/ -v
```

**Coverage hiện tại:**
- Unit tests: salary · experience · location · role · seniority · work_mode · domain · skills
- Quality unit tests: completeness · validity · accuracy · uniqueness · timeliness · reporter
- Integration test: toàn bộ pipeline flow Bronze → Silver

---

## Lộ trình phát triển

- [ ] Thêm nguồn dữ liệu thứ hai (ITviec)
- [ ] Scheduling tự động (APScheduler / cron)
- [ ] Containerization (Docker + docker-compose)
- [ ] CI pipeline (GitHub Actions)
- [ ] File logging cho Python pipeline
- [ ] Date-partitioned Silver snapshot (không overwrite)
- [ ] Bronze quality check trước khi transform
- [ ] Mô hình dự đoán lương

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Ingestion | Node.js 20 · Playwright · playwright-extra-stealth · Cheerio |
| Transform | Python 3.12 · Pandas · PyArrow |
| Quality | Python (thuần, 5 dimensions) |
| Gold | Pandas aggregations → Parquet |
| Serving | Streamlit · Plotly |
| Testing | Pytest (unit + integration) |
| Env management | uv |
| Config | YAML |
