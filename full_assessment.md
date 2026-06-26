# Đánh giá toàn diện & Đề xuất tái cấu trúc — data_job

> Tổng hợp phân tích hệ thống hiện tại, đề xuất cải tiến, thiết kế tái cấu trúc và cấu trúc codebase khi mở rộng multi-source (ITviec).

---

## Mục lục

1. [Đánh giá mức độ chuyên nghiệp hiện tại](#1-đánh-giá-mức-độ-chuyên-nghiệp-hiện-tại)
2. [Điểm mạnh cần giữ lại](#2-điểm-mạnh-cần-giữ-lại)
3. [Khoảng cách với production-grade](#3-khoảng-cách-với-production-grade)
4. [Cải tiến đề xuất (không phức tạp)](#4-cải-tiến-đề-xuất-không-phức-tạp)
5. [Nếu tái cấu trúc — thiết kế theo 3 tầng quyết định](#5-nếu-tái-cấu-trúc--thiết-kế-theo-3-tầng-quyết-định)
6. [Cấu trúc codebase đề xuất khi thêm ITviec](#6-cấu-trúc-codebase-đề-xuất-khi-thêm-itviec)
7. [Lộ trình triển khai theo mức độ](#7-lộ-trình-triển-khai-theo-mức-độ)
8. [Kết luận thẳng thắn](#8-kết-luận-thẳng-thắn)

---

## 1. Đánh giá mức độ chuyên nghiệp hiện tại

```
Student project ──────────────────────────── Production system
      1    2    3    4    5    6    7    8    9    10

                          ↑
                     Hiện tại (~4.5)
                                              ↑
                                    Mục tiêu (~8.0)
```

Project có kiến trúc Medallion đúng, có data quality framework, có tests, có Gold Layer, có CLI — những thứ này đẩy lên khỏi mức "student project". Nhưng nếu một senior data engineer đọc codebase này, họ sẽ dừng lại ở 6 điểm sau.

| Dimension | Điểm hiện tại | Vấn đề cốt lõi |
|-----------|:---:|---|
| **Cấu trúc** | 5/10 | Bronze phẳng, reader hardcode filename và source |
| **Contract giữa tầng** | 3/10 | Không có schema validation Bronze → Transform |
| **Orchestration** | 3/10 | PowerShell → chỉ chạy được trên Windows |
| **Config management** | 4/10 | 500+ dòng runtime + constants + domain lẫn lộn |
| **Observability** | 4/10 | Chỉ stdout, không file log, không run summary |
| **Portability** | 3/10 | Không có Docker, "chỉ chạy trên máy tôi" |

---

## 2. Điểm mạnh cần giữ lại

Đây là những phần được thiết kế đúng hướng — **không nên refactor lại từ đầu**.

**Medallion Architecture đúng tinh thần.** Bronze → Silver → Gold không phải đặt tên cho vui. Gold Layer pre-aggregated thay vì để dashboard tự tính là quyết định đúng.

**8 processors độc lập nhau.** Mỗi concern (salary, experience, location, skills, domain, role, seniority, work_mode) là một file riêng. Single Responsibility Principle được áp dụng đúng. Khi thêm source mới, các processor này không cần thay đổi gì.

**Data Quality framework 5 chiều.** Completeness / Validity / Accuracy / Uniqueness / Timeliness với config-driven thresholds, exit code để dừng pipeline khi lỗi, report MD và JSON theo date-partitioned directory. Rất ít project cá nhân đạt được mức này.

**`SilverJob` dataclass có typed schema.** `from_dict()` và `to_dict()`, type hints đầy đủ — dễ maintain và dễ validate.

**Tests có cấu trúc đúng.** Unit test và integration test tách biệt, `conftest.py`, `fixtures/` riêng. Integration test dùng `tmp_path` đúng cách.

**Crawler có checkpoint và upsert logic.** Không mất data khi interrupt, không crawl lại từ đầu — tư duy đúng của production crawler.

---

## 3. Khoảng cách với production-grade

### 3.1 Coupling quá chặt giữa các tầng

`reader.py` biết tên file cụ thể của Bronze (`jobs_all.json`, `jobs_detail.json`, `job_text_final.json`). `pipeline.py` gọi trực tiếp `reader.py`, `writer.py`, quality runner — không có interface trung gian. Thêm source mới đòi hỏi sửa nhiều file cùng lúc.

### 3.2 Không có contract rõ ràng giữa Bronze → Transform

Nếu crawler thay đổi field name, transform sẽ chạy nhưng cho ra kết quả sai hoàn toàn — không có gì báo lỗi. Không có Bronze schema validation. Pipeline fail thầm lặng với kết quả sai thay vì fail nhanh với thông báo rõ.

### 3.3 Orchestration phụ thuộc PowerShell

`cli.py run` và `Makefile all/run` gọi `powershell` trực tiếp. Trên Linux / macOS / Docker / CI, lệnh này fail hoàn toàn. Đây là dấu hiệu rõ nhất cho thấy pipeline chưa được thiết kế để chạy trên môi trường khác ngoài Windows của tác giả.

### 3.4 Bronze là thư mục phẳng — không hỗ trợ multi-source

Nếu chạy TopCV và ITviec đồng thời, các file `jobs_list.json` sẽ đè lên nhau. Không có cách nào phân biệt dữ liệu từ source nào mà không đọc nội dung từng file. `source` field hardcode là `"TopCV"` mọi nơi.

### 3.5 Config và constants lẫn lộn trong một file 500+ dòng

`config.py` chứa ba loại thông tin hoàn toàn khác nhau: runtime config (thay đổi theo môi trường), business constants (thay đổi theo logic), domain knowledge (LOCATION_MAPPING, SKILL_KEYWORDS). Không phân biệt được ai cần sửa cái gì.

### 3.6 Không có observability

Khi pipeline chạy scheduled lúc 2 giờ sáng và fail — bạn biết gì? Không có alert, không có file log, không có run summary. Chỉ có stdout đã biến mất. Python pipeline chỉ log ra stdout trong khi crawler Node.js có `crawl.log` — không nhất quán.

### 3.7 So sánh kiến trúc: Hiện tại vs Đề xuất

```
HIỆN TẠI                              ĐỀ XUẤT (multi-source)
─────────────────────────────         ─────────────────────────────────────
TopCV crawlers (3 scripts)            TopCV crawlers    ITviec crawlers
        │                                    │                  │
        ▼                                    ▼                  ▼
data/bronze/ (phẳng)                  bronze/topcv/     bronze/itviec/
  jobs_all.json                         jobs_list.json    jobs_list.json
  jobs_detail.json                      jobs_detail.json  jobs_detail.json
  job_text_final.json                          │                  │
        │                                      └────────┬─────────┘
        ▼                                               ▼
reader.py                                     source_reader.py
  hardcode 3 filename                           iter source dirs
  source = "TopCV" default                      inject source field
        │                                               │
        ▼                                               ▼
8 processors                          8 processors (không đổi, reusable)
  không biết source                     source-agnostic
        │                                               │
        ▼                                               ▼
Silver · Gold · Dashboard             Silver · Gold · Dashboard
  mixed data, no source tag              có source field, so sánh được

Thêm nguồn mới                        Thêm nguồn mới
= sửa reader + pipeline                = thêm 1 thư mục + 1 crawler
```

---

## 4. Cải tiến đề xuất (không phức tạp)

> Chỉ cải thiện quy trình hiện tại để sẵn sàng mở rộng — không viết lại từ đầu.

### Thay đổi 1 — Bronze namespace theo source *(impact lớn nhất, thay đổi nhỏ nhất)*

**Cấu trúc mới:**

```
data/bronze/
├── topcv/
│   ├── jobs_list.json          ← đổi tên từ jobs_all.json
│   ├── jobs_detail.json
│   └── job_text_final.json
└── itviec/                     ← sau này
    ├── jobs_list.json
    └── jobs_detail.json
```

**Việc cần làm:** Sửa `outputFile` trong 3 crawler scripts:

```
../../data/bronze/jobs_all.json        →  ../../data/bronze/topcv/jobs_list.json
../../data/bronze/jobs_detail.json     →  ../../data/bronze/topcv/jobs_detail.json
../../data/bronze/job_text_final.json  →  ../../data/bronze/topcv/job_text_final.json
```

---

### Thay đổi 2 — `reader.py` biết đọc theo source directory

Không xóa logic cũ — thêm function `load_source_dir()` vào cùng file:

```python
def load_source_dir(bronze_dir: Path) -> List[Dict[str, Any]]:
    """
    Đọc tất cả source subdirectories trong bronze_dir.
    Mỗi subdir = 1 source. Inject 'source' field từ tên subdir.
    """
    all_records = []
    for source_dir in sorted(bronze_dir.iterdir()):
        if not source_dir.is_dir():
            continue
        source_name = source_dir.name          # "topcv" hoặc "itviec"
        records = merge_source(source_dir, source_name)
        all_records.extend(records)
    return all_records


def merge_source(source_dir: Path, source_name: str) -> List[Dict]:
    """Merge files trong 1 source dir, gắn source field."""
    # logic tương tự merge_data() hiện tại
    # ...
    for record in result:
        record['source'] = source_name.capitalize()  # "Topcv" → normalize thêm nếu cần
    return result
```

`pipeline.py` gọi `load_source_dir()` thay vì `merge_data()`. Không có gì khác thay đổi.

---

### Thay đổi 3 — `config.yaml` khai báo sources

```yaml
crawler:
  sources:
    - name: topcv
      enabled: true
      roles:
        - data-engineer
        - data-analyst
        - data-scientist
        - business-intelligence
    - name: itviec
      enabled: false     # bật khi có crawler
      roles:
        - data-engineer
        - data-analyst
```

CLI `crawl` đọc config này, chỉ chạy source nào `enabled: true`. Bật thêm nguồn chỉ cần sửa 1 dòng config.

---

### Thay đổi 4 — Đảm bảo `source` field được set đúng trong `SilverJob`

`silver_schema.py` đã có `source: str = "TopCV"` nhưng `pipeline.py` fallback về default khi record không có field này. Cần đảm bảo `source` từ `merge_source()` được truyền đúng vào `SilverJob`:

```python
# pipeline.py — process_record()
silver_job = SilverJob(
    ...
    source=record.get('source', 'Unknown'),  # không dùng hardcode "TopCV"
    ...
)
```

---

### Thay đổi 5 — Fix `.gitignore` Windows absolute path

**Hiện tại (sai):**
```gitignore
D:\topcv-data-engineer\crawlers\node_modules
D:\topcv-data-engineer\future.md
```

**Sửa thành:**
```gitignore
crawlers/node_modules/
```

File `future.md` không cần gitignore — nếu muốn không push thì xóa file đó đi, không phải gitignore nó.

---

## 5. Nếu tái cấu trúc — thiết kế theo 3 tầng quyết định

Không phải viết lại từ đầu. Tái cấu trúc có nghĩa là **giữ nguyên business logic** (8 processors, quality checks, Gold builder), **thay đổi cách các thành phần kết nối với nhau**.

---

### Tầng 1 — Structure (Tổ chức code)

**Vấn đề hiện tại:** `config.py` hơn 500 dòng chứa ba loại thông tin hoàn toàn khác nhau lẫn lộn nhau.

**Đề xuất tách thành 3 file:**

```
transform/src/config/
├── runtime.py        ← paths, thresholds, feature switches
│                       thay đổi theo môi trường (dev/staging/prod)
├── constants.py      ← ROLE_MAPPING, SKILL_KEYWORDS, SENIORITY_LEVELS
│                       thay đổi theo business logic
└── domain.py         ← LOCATION_MAPPING, STOPWORDS_VI, COMPANY_NAMES
                        thay đổi theo domain knowledge
```

**Lý do tách:**

- Khi deploy lên server, chỉ `runtime.py` cần biết về đường dẫn thực tế.
- Khi thêm skill mới, chỉ `constants.py` cần sửa — không cần đọc qua business logic.
- Người maintain domain knowledge (thêm thành phố, thêm công ty filter) không cần hiểu code pipeline.

---

### Tầng 2 — Contract (Giao tiếp giữa tầng)

**Vấn đề hiện tại:** Bronze → Transform không có validation. Nếu crawler thay đổi field name, pipeline chạy xuyên qua hàng nghìn records rồi mới phát hiện kết quả sai.

**Đề xuất thêm một file duy nhất:**

```python
# transform/src/schemas/bronze_contract.py

REQUIRED_FIELDS = {"title", "company", "url", "crawled_at"}

OPTIONAL_FIELDS = {
    "salary", "experience", "location",
    "description", "requirements", "benefits"
}

def validate_bronze_record(record: dict, source: str) -> tuple[bool, str]:
    """
    Validate một Bronze record trước khi đưa vào transform.
    Trả về (True, "") nếu hợp lệ, (False, reason) nếu không.
    """
    missing = REQUIRED_FIELDS - set(record.keys())
    if missing:
        return False, f"[{source}] Thiếu required fields: {missing}"

    if not record.get("url", "").startswith("http"):
        return False, f"[{source}] URL không hợp lệ: {record.get('url')}"

    if not record.get("title", "").strip():
        return False, f"[{source}] Title rỗng"

    return True, ""
```

**Tích hợp vào `pipeline.py` trước bước process:**

```python
valid_records, invalid_records = [], []
for record in raw_records:
    ok, reason = validate_bronze_record(record, record.get('source', 'unknown'))
    if ok:
        valid_records.append(record)
    else:
        invalid_records.append({"record": record, "reason": reason})
        logger.warning(reason)

logger.info(f"Bronze validation: {len(valid_records)} valid, {len(invalid_records)} invalid")
```

**Kết quả:** Khi ITviec crawler output sai field name, pipeline fail ngay lập tức với thông báo rõ ràng.

---

### Tầng 3 — Runtime (Chạy như thế nào)

Đây là khoảng cách lớn nhất. Pipeline hiện tại chỉ tồn tại ở dạng "chạy thủ công một lần".

#### 3.a — Run summary JSON

Thêm `run_summary.json` sau mỗi lần chạy pipeline:

```json
{
  "run_id": "2026-06-23T02:00:00",
  "sources": ["topcv", "itviec"],
  "bronze_records": 1240,
  "silver_records": 1187,
  "invalid_bronze_records": 53,
  "silver_null_rate": 0.043,
  "quality_status": "PASS",
  "duration_seconds": 142,
  "gold_tables_built": 9
}
```

Lưu tại `data/runs/<run_id>/summary.json`. Sau 10 lần chạy, bạn có lịch sử để debug và so sánh.

#### 3.b — File logging cho Python pipeline

Hiện tại crawler Node.js có `crawl.log`, Python pipeline chỉ log ra stdout. Thêm `RotatingFileHandler` trong `main.py`:

```python
from logging.handlers import RotatingFileHandler

def setup_logging():
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    handlers = [
        logging.StreamHandler(),
        RotatingFileHandler(
            logs_dir / "pipeline.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )
```

#### 3.c — Scheduling đơn giản

Không cần Airflow. Cron job là đủ cho giai đoạn này:

```bash
# Chạy mỗi sáng thứ Hai và thứ Năm lúc 2h sáng
0 2 * * 1,4 cd /path/to/data_job && uv run python cli.py run >> logs/cron.log 2>&1
```

#### 3.d — Cross-platform CLI (bỏ PowerShell)

Sửa `cli.py run` gọi Python trực tiếp thay vì spawn PowerShell:

```python
# cli.py — run command
@app.command()
def run(
    headless: bool = typer.Option(True, "--headless/--headed"),
    roles: str = typer.Option("", "--roles", help="Comma-separated roles"),
    no_gold: bool = typer.Option(False, "--no-gold"),
    no_quality: bool = typer.Option(False, "--no-quality"),
):
    """Chạy toàn bộ pipeline: crawl → transform → quality → gold."""
    from transform.src.orchestrator.pipeline import run_pipeline

    typer.secho("===== BẮT ĐẦU PIPELINE =====", fg=typer.colors.CYAN)
    crawl(task="all", headless=headless, roles=roles)
    exit_code = run_pipeline(
        skip_gold=no_gold,
        skip_quality=no_quality
    )
    raise typer.Exit(exit_code)
```

Sửa `makefile`:

```makefile
run:
    uv run python cli.py run

crawl:
    uv run python cli.py crawl all

transform:
    uv run python cli.py transform

clean:
    uv run python cli.py clean
```

#### 3.e — Dockerfile đơn giản

```dockerfile
FROM python:3.12-slim

# Node.js 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY . .
RUN uv sync && cd crawlers && npm install

CMD ["uv", "run", "python", "cli.py", "run"]
```

`docker-compose.yml`:

```yaml
services:
  pipeline:
    build: .
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    command: uv run python cli.py run
```

Sau khi có Dockerfile: `docker compose up` là xong — không cần cài Python, Node.js, uv trên máy.

---

## 6. Cấu trúc codebase đề xuất khi thêm ITviec

> Nguyên tắc thiết kế: **8 processors không thay đổi một chữ** — chỉ crawlers và reader biết về source.

```
data_job/
│
├── cli.py                              # thêm routing cho --source flag
├── config.yaml                         # thêm sources config
├── pyproject.toml                      # requires-python = ">=3.12"
├── makefile                            # bỏ PowerShell, gọi cli.py trực tiếp
├── Dockerfile                          # THÊM MỚI
├── docker-compose.yml                  # THÊM MỚI
│
├── crawlers/
│   ├── package.json
│   └── src/
│       ├── topcv/                      ← nhóm theo source (move từ src/)
│       │   ├── list-crawler-multi.js   # hiện có, chỉ đổi outputFile path
│       │   ├── detail-crawler.js       # hiện có, chỉ đổi outputFile path
│       │   └── text-crawler.js         # hiện có, chỉ đổi outputFile path
│       └── itviec/                     ← THÊM MỚI
│           ├── list-crawler.js         # crawl trang danh sách ITviec
│           └── detail-crawler.js       # crawl chi tiết từng job
│
├── data/
│   ├── bronze/
│   │   ├── topcv/                      ← namespaced (đổi từ phẳng)
│   │   │   ├── jobs_list.json
│   │   │   ├── jobs_detail.json
│   │   │   ├── job_text_final.json
│   │   │   └── checkpoint_*.json
│   │   └── itviec/                     ← THÊM MỚI (khi có crawler)
│   │       ├── jobs_list.json
│   │       ├── jobs_detail.json
│   │       └── checkpoint_*.json
│   ├── silver/
│   │   └── jobs_silver.parquet         # có source="Topcv" / "Itviec"
│   ├── gold/
│   │   └── *.parquet                   # 9 bảng, không đổi gì
│   ├── quality/
│   │   └── <YYYY-MM-DD>/               # report MD + JSON theo ngày
│   └── runs/                           # THÊM MỚI
│       └── <run_id>/
│           └── summary.json            # run metadata, duration, record counts
│
├── logs/                               # THÊM MỚI
│   ├── pipeline.log                    # Python transform logs
│   └── cron.log                        # scheduled run logs
│
├── transform/
│   └── src/
│       ├── config/                     # TÁCH TỪ config.py — THÊM MỚI
│       │   ├── __init__.py
│       │   ├── runtime.py              # paths, thresholds, feature switches
│       │   ├── constants.py            # ROLE_MAPPING, SKILL_KEYWORDS
│       │   └── domain.py               # LOCATION_MAPPING, STOPWORDS_VI
│       │
│       ├── io/
│       │   ├── reader.py               ← thêm load_source_dir()
│       │   └── writer.py               # không đổi
│       │
│       ├── processors/                 # KHÔNG ĐỔI GÌ — source-agnostic
│       │   ├── salary.py
│       │   ├── experience.py
│       │   ├── location.py
│       │   ├── skills.py
│       │   ├── domain.py
│       │   ├── role.py
│       │   ├── seniority.py
│       │   └── work_mode.py
│       │
│       ├── orchestrator/
│       │   └── pipeline.py             ← gọi load_source_dir(), validate_bronze, run summary
│       │
│       ├── schemas/
│       │   ├── silver_schema.py        # không đổi, source field đã có
│       │   └── bronze_contract.py      # THÊM MỚI — required/optional fields + validate()
│       │
│       ├── gold/
│       │   └── gold_builder.py         # không đổi
│       │
│       └── quality/                    # không đổi
│           ├── runner.py
│           ├── completeness.py
│           ├── validity.py
│           ├── accuracy.py
│           ├── uniqueness.py
│           ├── timeliness.py
│           └── reporter.py
│
├── dashboard/
│   └── app.py                          # thêm filter theo source nếu muốn
│
└── notebooks/
    └── ...
```

---

### Luồng khi thêm ITviec — chỉ cần làm 4 việc

```
Bước 1: Viết crawlers/src/itviec/list-crawler.js
        → output: data/bronze/itviec/jobs_list.json
        → JSON schema giống TopCV: {title, company, url, salary, location, crawled_at, ...}

Bước 2: Viết crawlers/src/itviec/detail-crawler.js
        → output: data/bronze/itviec/jobs_detail.json

Bước 3: config.yaml → đặt itviec.enabled = true

Bước 4: uv run python cli.py run --roles "data-engineer"
        → reader.py tự tìm data/bronze/itviec/
        → validate_bronze_record() kiểm tra schema
        → inject source="Itviec" vào mỗi record
        → 8 processors xử lý y chang TopCV
        → Silver có cả TopCV + ITviec, phân biệt qua cột source
```

### Contract duy nhất giữa crawler và transform

ITviec crawler **phải output đúng field names** sau đây. Nếu ITviec dùng tên field khác trên HTML, xử lý rename ngay trong crawler — không để transform layer phải biết về sự khác biệt:

| Field | Bắt buộc | Ví dụ |
|-------|:---:|-------|
| `title` | ✅ | "Senior Data Engineer" |
| `company` | ✅ | "FPT Software" |
| `url` | ✅ | "https://itviec.com/it-jobs/..." |
| `crawled_at` | ✅ | "2026-06-23T10:00:00" |
| `location` | — | "Hà Nội" |
| `salary` | — | "20 - 35 triệu" |
| `experience` | — | "3 - 5 năm" |
| `description` | — | "..." |
| `requirements` | — | "..." |
| `benefits` | — | "..." |

---

## 7. Lộ trình triển khai theo mức độ

### Mức Tối thiểu — 2–3 giờ
*Pipeline sẵn sàng nhận nhiều source*

| Task | File cần sửa |
|------|-------------|
| Rename bronze dirs trong 3 crawler scripts | `crawlers/src/topcv/*.js` |
| Thêm `load_source_dir()` vào `reader.py` | `transform/src/io/reader.py` |
| `pipeline.py` gọi `load_source_dir()` thay `merge_data()` | `transform/src/orchestrator/pipeline.py` |
| `SilverJob` nhận `source` từ record, không hardcode | `transform/src/orchestrator/pipeline.py` |
| Fix `.gitignore` Windows absolute path | `.gitignore` |
| Fix `pyproject.toml` requires-python = ">=3.12" | `pyproject.toml` |

---

### Mức Đủ dùng — 1 ngày
*Bật/tắt source qua config, cross-platform*

| Task | File cần sửa |
|------|-------------|
| `config.yaml` thêm sources section | `config.yaml` |
| CLI routing `--source` flag | `cli.py` |
| Bỏ PowerShell trong `cli.py run` | `cli.py` |
| Bỏ PowerShell trong `makefile` | `makefile` |
| Thêm `bronze_contract.py` và validate trước transform | `transform/src/schemas/bronze_contract.py` |
| Thêm file logging cho Python pipeline | `transform/src/main.py` |

---

### Mức Hoàn chỉnh — 1 tuần
*Multi-source thực sự, production-ready*

| Task | Effort |
|------|--------|
| Viết ITviec crawlers (list + detail) | 3–5 ngày |
| Tách `config.py` thành 3 file (runtime / constants / domain) | 2–3 giờ |
| Thêm `run_summary.json` vào pipeline | 1–2 giờ |
| `Dockerfile` + `docker-compose.yml` | 3–4 giờ |
| Cron job hoặc APScheduler | 1 giờ |
| GitHub Actions CI (chạy pytest tự động) | 2 giờ |

---

## 8. Kết luận thẳng thắn

Project hiện tại cho thấy bạn **hiểu data engineering** — Medallion Architecture đúng, data quality đúng hướng, Gold Layer đúng chỗ, 8 processors độc lập nhau. Đây là thứ không phải ai cũng làm được ở level này.

Nhưng để từ "hiểu" sang "professional", cần thêm một tư duy: **thiết kế cho người khác và cho tương lai**, không chỉ cho mình và cho hôm nay.

| Câu hỏi | Trạng thái hiện tại | Sau khi hoàn thiện |
|---------|--------------------|--------------------|
| Người khác clone repo có chạy được không? | ❌ Phụ thuộc Windows + PowerShell | ✅ Docker compose up |
| Khi pipeline fail lúc 3h sáng bạn có biết không? | ❌ Không có log, không có summary | ✅ File log + run summary JSON |
| Khi thêm ITviec có phải sửa nhiều file không? | ❌ Sửa reader + pipeline + config | ✅ Thêm 1 thư mục + 1 crawler |
| Crawler thay đổi output có phát hiện được ngay không? | ❌ Fail thầm lặng với kết quả sai | ✅ Fail nhanh, thông báo rõ |
| Thêm nguồn mới có cần hiểu transform code không? | ❌ Có, phải sửa reader.py | ✅ Không, chỉ cần đúng contract |

**Những thứ này không phức tạp về kỹ thuật** — nhưng chính vì không có chúng mà khoảng cách giữa "chạy được" và "professional" vẫn còn đó.

Làm đủ mức Tối thiểu + Đủ dùng (khoảng 1–2 ngày): project lên ~7/10, đủ để trình bày trong interview với sự tự tin. Hoàn thành thêm ITviec crawler và Dockerfile: ~8.5/10 — portfolio-grade thực sự.
