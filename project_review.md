# Phân tích & Đề xuất cải tiến — Data Job Pipeline

> **Phạm vi:** Toàn bộ repo `data_job-main` sau khi đọc từng file.
> **Mục tiêu:** Đưa project từ trạng thái "hoạt động được" lên "production-grade".

---

## Mục lục

1. [Tổng quan kiến trúc thực tế](#1-tổng-quan-kiến-trúc-thực-tế)
2. [Điểm mạnh cần giữ lại](#2-điểm-mạnh-cần-giữ-lại)
3. [P0 — Lỗi nghiêm trọng, phá vỡ tính năng](#3-p0--lỗi-nghiêm-trọng-phá-vỡ-tính-năng)
4. [P1 — Lỗi logic, hành vi sai nhưng không crash](#4-p1--lỗi-logic-hành-vi-sai-nhưng-không-crash)
5. [P2 — Chất lượng code, maintainability](#5-p2--chất-lượng-code-maintainability)
6. [P3 — Kiến trúc cần hoàn thiện](#6-p3--kiến-trúc-cần-hoàn-thiện)
7. [P4 — Production readiness](#7-p4--production-readiness)
8. [Lộ trình triển khai theo Sprint](#8-lộ-trình-triển-khai-theo-sprint)
9. [Ma trận đánh giá tổng thể](#9-ma-trận-đánh-giá-tổng-thể)

---

## 1. Tổng quan kiến trúc thực tế

```
TopCV (Playwright/Stealth)
        │
        ▼
  Bronze Layer          ← jobs_all.json, jobs_detail.json, job_text_final.json
  (JSON + checkpoint)
        │
        ▼
  pipeline.py           ← reader.py (merge 3 files) → 8 processors → SilverJob
        │
        ├──► Data Quality (5 stages) → report MD/JSON theo ngày
        │
        ▼
  Silver Layer          ← jobs_silver.parquet
        │
        ▼ (đường dẫn trực tiếp, bỏ qua Gold)
  Dashboard             ← Streamlit + Plotly

  Gold Layer            ← khai báo trong config.yaml nhưng CHƯA TỒN TẠI
```

**Công nghệ stack:**

| Tầng | Công nghệ |
|------|-----------|
| Ingestion | Node.js + Playwright + playwright-extra-stealth |
| Transform | Python + Pandas + PyArrow |
| Orchestration | Typer CLI + PowerShell script |
| Quality | Python thuần (5 dimension) |
| Storage | JSON (Bronze), Parquet (Silver) |
| Serving | Streamlit + Plotly |
| Test | Pytest (unit + integration) |
| Env | uv |

---

## 2. Điểm mạnh cần giữ lại

Đây là những phần được thiết kế đúng hướng — **không nên refactor lại từ đầu**.

**Cấu trúc module processors:** Mỗi concern (salary, experience, role, skills, location, seniority, work_mode, domain) là một file riêng, độc lập, không phụ thuộc lẫn nhau. Đây là Single Responsibility Principle được áp dụng đúng.

**Data Quality framework 5 chiều:** Completeness / Validity / Accuracy / Uniqueness / Timeliness — đây là cấu trúc chuẩn của data quality trong môi trường doanh nghiệp. Có config-driven thresholds, có exit code để dừng pipeline khi lỗi, có report MD và JSON theo date-partitioned directory. Rất ít project cá nhân đạt được mức này.

**Crawler với checkpoint và upsert logic:** Không mất data khi interrupt, không crawl lại từ đầu — tư duy đúng của production crawler.

**Test có cấu trúc rõ ràng:** Unit test và integration test tách biệt, có `conftest.py`, có `fixtures/` riêng. Integration test dùng `tmp_path` đúng cách, không làm dirty working directory.

**SilverJob dataclass:** Schema rõ ràng, có `from_dict()` và `to_dict()`, type hints đầy đủ — dễ maintain và dễ validate.

**`config.yaml` + `config_loader.py`:** Cấu hình tập trung, có fallback `get_default_config()` khi không có file.

---

## 3. P0 — Lỗi nghiêm trọng, phá vỡ tính năng

> Cần sửa **ngay lập tức** trước khi làm bất cứ việc gì khác.

---

### P0-1: `pyproject.toml` yêu cầu Python >=3.14 — phiên bản không tồn tại

**File:** `pyproject.toml`

```toml
# Hiện tại — SAI
requires-python = ">=3.14"

# Sửa thành
requires-python = ">=3.12"
```

Python 3.14 đang ở giai đoạn alpha (dự kiến ra tháng 10/2025). Bất kỳ CI pipeline, Docker image, hoặc máy của người khác khi clone repo đều fail ngay ở bước `uv sync`. Đây là lỗi đầu tiên mọi người gặp.

---

### P0-2: `cli.py run` và `Makefile all/run` phụ thuộc PowerShell — chỉ chạy được trên Windows

**File:** `cli.py`, `makefile`

```python
# cli.py — run command hiện tại
cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]
```

```makefile
# makefile — run target hiện tại
run:
    powershell -ExecutionPolicy Bypass -File run_pipeline.ps1
all: run
```

Lệnh `cli.py run` và `make run` / `make all` gọi `powershell` trực tiếp. Trên Linux/macOS (server, Docker, CI), lệnh này fail hoàn toàn. `makefile` còn đặt `all: run` — target mặc định trên mọi `make` đều phụ thuộc PowerShell.

**Sửa `cli.py`:**

```python
@app.command()
def run(headless: bool = typer.Option(True, "--headless/--headed")):
    """Chạy toàn bộ pipeline: crawl all + transform."""
    typer.secho("===== BẮT ĐẦU PIPELINE =====", fg=typer.colors.CYAN)
    
    # Gọi trực tiếp các hàm Python thay vì spawn PowerShell
    ctx = typer.Context(run)  # reuse current context
    crawl(task="all", headless=headless)
    transform(format="parquet")
    
    typer.secho("✅ Pipeline hoàn tất!", fg=typer.colors.GREEN)
```

**Sửa `makefile`:**

```makefile
run:
    @echo "=== Running full pipeline ==="
    uv run python cli.py crawl all
    uv run python cli.py transform

all: crawl transform
```

---

### P0-3: CLI `--format` option trong `transform` command không có tác dụng

**File:** `cli.py`, `transform/src/main.py`

```python
# cli.py — nhận option --format
def transform(format: str = typer.Option("parquet", "--format")):
    cmd = ["uv", "run", "python", "-m", "transform.src.main"]  # không truyền format!
    run_command(cmd, cwd=PROJECT_ROOT)

# transform/src/main.py — hardcode
def main():
    exit_code = run_pipeline(output_format="parquet")  # luôn là parquet
```

Option `--format csv` được người dùng truyền vào nhưng bị nuốt mất. Người dùng khi chạy `cli.py transform --format csv` sẽ vẫn nhận được file Parquet.

**Sửa `cli.py`:**

```python
@app.command()
def transform(format: str = typer.Option("parquet", "--format")):
    from transform.src.orchestrator.pipeline import run_pipeline
    result = run_pipeline(output_format=format)
    if result != 0:
        raise typer.Exit(result)
```

---

### P0-4: `import re` nằm bên trong vòng lặp `merge_data()`

**File:** `transform/src/io/reader.py`, cuối function `merge_data()`

```python
# Hiện tại — SAI (import trong vòng lặp)
for url, record in merged.items():
    if 'id' not in record or not record.get('id'):
        import re  # ← đây
        match = re.search(r'/(\d+)\.html', url)
```

Import trong vòng lặp không crash nhưng không hiệu quả và vi phạm convention Python cơ bản (PEP 8: all imports at top of file). Python cache lại import nên không gây ra overhead nghiêm trọng, nhưng trong code review thực tế đây là red flag ngay lập tức.

**Sửa:** Đưa `import re` lên đầu file (đã có `re` được dùng ở chỗ khác trong file).

---

### P0-5: `dashboard/app.py` nằm sai thư mục so với README và `cli.py`

**File:** `README.md`, `cli.py`

```bash
# README hướng dẫn:
streamlit run app.py  # ← file này không tồn tại ở root

# File thực tế nằm ở:
dashboard/app.py
```

Người dùng làm theo README sẽ nhận lỗi `FileNotFoundError` ngay lập tức. README cũng đặt `app.py` trong cấu trúc thư mục ở root nhưng thực tế file nằm trong `dashboard/`.

**Sửa README:**
```bash
streamlit run dashboard/app.py
```

---

## 4. P1 — Lỗi logic, hành vi sai nhưng không crash

---

### P1-1: `get_role_from_title()` trả về `"Data Engineer"` cho mọi title không khớp

**File:** `transform/src/utils/config.py`

```python
def get_role_from_title(title: str) -> str:
    title_lower = title.lower()
    for pattern, role in ROLE_MAPPING:
        if re.search(pattern, title_lower):
            return role
    return "Data Engineer"  # ← default sai
```

Khi crawler lấy được job không phải ngành Data (ví dụ "Backend Engineer", "Product Manager", "QA Engineer"), chúng đều bị gán `normalized_role = "Data Engineer"`. Điều này làm nhiễu toàn bộ analytics — số lượng Data Engineer bị inflate, các dashboard phân tích role trở nên vô nghĩa.

**Sửa:**

```python
def get_role_from_title(title: str) -> Optional[str]:
    title_lower = title.lower()
    for pattern, role in ROLE_MAPPING:
        if re.search(pattern, title_lower):
            return role
    return None  # Không biết → để None, lọc sau ở analytics
```

Sau đó cập nhật `completeness.py` — `normalized_role` là trường quan trọng, null rate cao sẽ kích hoạt WARNING/ERROR đúng chỗ.

---

### P1-2: `check_completeness()` override tham số `field_error_thresholds` đầu vào ngay bên trong hàm

**File:** `transform/src/quality/completeness.py`

```python
def check_completeness(
    df,
    warning_threshold=0.95,
    error_threshold=0.80,
    field_error_thresholds: Dict[str, float] = None  # ← tham số này
):
    if field_error_thresholds is None:
        field_error_thresholds = {}
    
    # ... 3 dòng sau:
    field_error_thresholds = {   # ← OVERRIDE hoàn toàn tham số đầu vào!
        'salary_min': 0.25,
        'salary_max': 0.25,
    }
```

Bất kỳ giá trị nào được truyền vào `field_error_thresholds` từ `config.yaml` (qua `runner.py`) đều bị nuốt mất. Config `field_overrides` trong `config.yaml` không có tác dụng gì. Đây là silent bug — không crash, không cảnh báo, nhưng cấu hình bị bỏ qua hoàn toàn.

**Sửa:**

```python
def check_completeness(
    df,
    warning_threshold=0.95,
    error_threshold=0.80,
    field_error_thresholds: Dict[str, float] = None
):
    # Dùng default thresholds cho các trường đặc biệt, nhưng merge với tham số đầu vào
    _default_overrides = {
        'salary_min': 0.25,
        'salary_max': 0.25,
    }
    # Tham số đầu vào override default (không bị overwrite ngược lại)
    resolved_overrides = {**_default_overrides, **(field_error_thresholds or {})}
```

---

### P1-3: `LOCATION_MAPPING` ánh xạ tên thành chính nó, không handle alias

**File:** `transform/src/utils/config.py`

```python
LOCATION_MAPPING = {
    "Hà Nội": "Hà Nội",          # ánh xạ sang chính nó — không có tác dụng
    "Hồ Chí Minh": "Hồ Chí Minh",
    ...
}
```

Và trong `location.py`:

```python
for city, normalized in LOCATION_MAPPING.items():
    if city.lower() in location.lower():
        return normalized
```

Mapping này không xử lý được các biến thể thực tế trong dữ liệu crawl: "TP.HCM", "TP Hồ Chí Minh", "Thành phố Hồ Chí Minh", "HCM", "Hà nội" (chữ thường), "Ha Noi" (không dấu). Kết quả là phần lớn địa điểm từ TopCV không được chuẩn hóa, rơi vào fallback trả về chuỗi gốc.

**Sửa:**

```python
LOCATION_MAPPING = {
    # Hồ Chí Minh — tất cả alias
    "hồ chí minh": "Hồ Chí Minh",
    "tp.hcm": "Hồ Chí Minh",
    "tp hcm": "Hồ Chí Minh",
    "thành phố hồ chí minh": "Hồ Chí Minh",
    "ho chi minh": "Hồ Chí Minh",
    "hcm": "Hồ Chí Minh",
    # Hà Nội
    "hà nội": "Hà Nội",
    "ha noi": "Hà Nội",
    "hn": "Hà Nội",
    # Đà Nẵng
    "đà nẵng": "Đà Nẵng",
    "da nang": "Đà Nẵng",
    ...
}
```

Và trong `clean_location()`, so sánh sau khi lowercase:

```python
location_lower = location.lower()
for alias, normalized in LOCATION_MAPPING.items():
    if alias in location_lower:
        return normalized
```

---

### P1-4: `timeliness.py` mutate DataFrame đầu vào trực tiếp

**File:** `transform/src/quality/timeliness.py`

```python
def check_timeliness(df: pd.DataFrame, ...) -> Dict[str, Any]:
    ...
    # ← Mutate df trực tiếp — side effect!
    df['crawled_at'] = df['crawled_at'].dt.tz_convert(None)
```

Hàm này nhận `df` và sửa trực tiếp cột `crawled_at` của nó. Nếu `run_pipeline()` tiếp tục dùng `df` sau khi gọi quality check, data đã bị thay đổi. Trong Python, Pandas DataFrame là pass-by-reference với assignment.

**Sửa:**

```python
# Không mutate input, dùng biến cục bộ
crawled = df['crawled_at'].copy()
if crawled.dt.tz is not None:
    crawled = crawled.dt.tz_convert(None)
now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
stale_mask = crawled < (now_utc - timedelta(days=days_threshold))
```

---

### P1-5: `quality/runner.py` import `typer` — vi phạm separation of concerns

**File:** `transform/src/quality/runner.py`

```python
import typer  # ← CLI framework trong business logic layer
...
typer.secho(f"❌ Không tìm thấy file Silver: {silver_file}", fg=typer.colors.RED, err=True)
```

Module quality là business logic — nó không nên biết về `typer` (CLI framework). Khi muốn gọi quality checks từ một context khác (Airflow DAG, API endpoint, unit test), dependency này bắt buộc phải có `typer` installed và sẽ gây ra vấn đề với `typer.colors` không hoạt động ngoài terminal.

**Sửa:** Dùng `logging` thay cho `typer.secho` trong `runner.py`:

```python
import logging
logger = logging.getLogger(__name__)

# Thay vì: typer.secho(f"❌ ...", fg=typer.colors.RED)
logger.error(f"Không tìm thấy file Silver: {silver_file}")
```

Chỉ dùng `typer` ở tầng CLI (`cli.py`). Tầng quality không được biết đến CLI framework.

---

### P1-6: `STOPWORDS_VI` chứa tên công ty — sai category

**File:** `transform/src/utils/config.py`

```python
STOPWORDS_VI = {
    ...
    # Thêm các từ xuất hiện nhiều trong skill_candidates.txt
    'viettel', 'cmc', 'fpt', 'vpbank', 'techcombank', 'vietinbank', 'agribank', 'bidv',
}
```

Tên công ty (Viettel, FPT, VPBank...) đặt trong `STOPWORDS_VI` sẽ bị loại bỏ khỏi kết quả phân tích kỹ năng (`skills.py` dùng STOPWORDS_VI để filter token). Điều này đúng cho việc trích xuất skill, nhưng sai về mặt design — đây không phải stopwords, đây là company names filter. Khi sau này thêm logic trích xuất company domain, set này sẽ làm nhiễu.

**Sửa:** Tách thành constant riêng:

```python
COMPANY_NAMES_TO_FILTER: Set[str] = {
    'viettel', 'cmc', 'fpt', 'vpbank', 'techcombank', 'vietinbank', 'agribank', 'bidv',
}
```

---

## 5. P2 — Chất lượng code, maintainability

---

### P2-1: Double `logging.basicConfig` — duplicate handlers

**File:** `transform/src/orchestrator/pipeline.py`

```python
# main.py đã setup logging:
logging.basicConfig(level=logging.INFO, format='...')

# pipeline.py setup lại:
logging.basicConfig(level=logging.INFO, format='...')  # ← duplicate
```

Gọi `basicConfig()` hai lần trong cùng một process không có tác dụng gì (Python bỏ qua lần thứ hai nếu root logger đã có handlers), nhưng trong một số cấu hình logging phức tạp hơn (file handler, structured logging) điều này tạo ra duplicate log entries. **Xóa** `logging.basicConfig` trong `pipeline.py`, chỉ để ở `main.py`.

---

### P2-2: `uniqueness.py` dùng `df.iterrows()` — anti-pattern với DataFrame lớn

**File:** `transform/src/quality/uniqueness.py`

```python
for idx, row in df.iterrows():  # ← O(n) Python loop
    role = row.get('normalized_role')
    title = row.get('title')
    ...
```

`iterrows()` là cách chậm nhất để duyệt DataFrame trong Pandas — với 10.000 records nó chạy được, nhưng khi scale lên 100K+ records nó sẽ trở thành bottleneck. Hơn nữa, `row.get()` không phải method của Pandas Series — cần dùng `row['col']` hoặc `row.get('col', default)` với `row` là Series.

**Sửa bằng vectorized operation:**

```python
def _check_role_title_consistency(df: pd.DataFrame) -> List[Dict]:
    mask = df['normalized_role'].notna() & df['title'].notna()
    sub = df[mask].copy()
    sub['title_lower'] = sub['title'].str.lower()
    
    def is_consistent(row):
        keywords = ROLE_KEYWORDS.get(row['normalized_role'], [])
        if not keywords:
            return False
        return any(kw in row['title_lower'] for kw in keywords)
    
    inconsistent = sub[~sub.apply(is_consistent, axis=1)]
    return inconsistent[['job_url', 'title', 'normalized_role']].to_dict('records')
```

---

### P2-3: Docstring đặt sai vị trí trong `check_completeness()`

**File:** `transform/src/quality/completeness.py`

```python
def check_completeness(
    df: pd.DataFrame,
    warning_threshold: float = 0.95,
    error_threshold: float = 0.80,
    field_error_thresholds: Dict[str, float] = None
):
    if field_error_thresholds is None:   # ← code trước docstring
        field_error_thresholds = {}
    """
    Kiểm tra tính đầy đủ...   # ← docstring sau code → Python không nhận ra đây là docstring
    """
```

Python docstring phải là statement đầu tiên trong function. Docstring đặt sau code sẽ bị Python coi là string literal bình thường, không phải `__doc__` của function. `help(check_completeness)` sẽ trả về `None`.

**Sửa:** Đưa docstring lên trước mọi code.

---

### P2-4: `skills.py` sử dụng hai approach song song nhưng approach 1 là subset của approach 2

**File:** `transform/src/processors/skills.py`

Code hiện tại có hai pass trên data:
1. **Token pass:** Tokenize text → lọc stopwords → kiểm tra từng token trong `SKILL_KEYWORDS` (chỉ bắt được unigrams)
2. **N-gram pass:** Split text → duyệt bigrams + trigrams → kiểm tra trong `SKILL_KEYWORDS`

Approach 1 (token pass) chỉ bắt được single-word skills. Approach 2 (n-gram pass) bắt được tất cả từ 1 đến 3 từ. Kết quả từ approach 1 là subset hoàn toàn của approach 2, nên approach 1 là redundant — nó chỉ thêm complexity mà không thêm value.

**Đề xuất:** Loại bỏ hoàn toàn "Cách 1" (token pass), chỉ giữ approach pattern-based với regex (sẽ chính xác hơn vì xử lý được boundary và special chars như `c++`, `c#`):

```python
# Một pass duy nhất với regex patterns
found_skills = set()
full_text_lower = full_text  # đã lowercase ở trên

for keyword in skill_keywords:
    pattern = _make_pattern(keyword)
    if re.search(pattern, full_text_lower, re.IGNORECASE):
        found_skills.add(keyword)

return sorted(found_skills - set(DOMAIN_KEYWORDS))
```

---

### P2-5: `.gitignore` list `pyproject.toml` là file có thể không push

**File:** `.gitignore`

```gitignore
pyproject.toml  # nếu bạn không muốn chia sẻ dependency (thường thì nên push)
```

`pyproject.toml` là file cấu hình project chuẩn (PEP 517/518). Bất kỳ ai clone repo đều cần file này để chạy `uv sync`. Nếu file này bị gitignore, repo không thể được reproduce bởi người khác. Comment trong .gitignore thể hiện sự do dự — **nên xóa dòng này khỏi .gitignore và luôn commit `pyproject.toml`**.

---

### P2-6: File trống — `future.md`, `transform/README.md`, `transform/src/docs.md`

3 file này có trong repo nhưng nội dung rỗng hoàn toàn. Trong một repo chuyên nghiệp, file trống là "broken window" — nó cho thấy project chưa hoàn thiện và khiến người đọc mất tin tưởng.

**Hành động:** Hoặc điền nội dung (ưu tiên `future.md` vì đây là roadmap), hoặc xóa các file này nếu chưa cần.

---

### P2-7: `node_modules` trong zip (cần verify `.gitignore`)

File zip được upload có chứa `crawlers/node_modules/` (31K+ files). Kiểm tra `.gitignore`:

```gitignore
# Hiện tại KHÔNG có dòng này!
# crawlers/node_modules/  ← THIẾU
```

Cần thêm vào `.gitignore`:

```gitignore
crawlers/node_modules/
```

---

## 6. P3 — Kiến trúc cần hoàn thiện

---

### P3-1: Gold Layer — khai báo nhưng chưa tồn tại

**Tình trạng:** `config.yaml` có `gold_dir: "data/gold"`. README đề cập Gold Layer. Nhưng không có file Python nào xây dựng Gold. Dashboard đọc trực tiếp từ Silver.

**Tại sao quan trọng:** Silver chứa 1 row = 1 job posting. Để analytics có ý nghĩa, cần pre-aggregate. Dashboard hiện tại làm aggregation on-the-fly mỗi lần load — không scale và không versioned.

**Đề xuất cấu trúc Gold:**

```
transform/src/gold/
├── __init__.py
├── builder.py          ← orchestrate xây Gold từ Silver
├── tables/
│   ├── fact_job_skills.py   ← explode skills → 1 row = 1 job × 1 skill
│   ├── agg_role_salary.py   ← salary median/avg theo role + seniority
│   ├── agg_skill_demand.py  ← skill frequency theo role và thời gian
│   └── agg_location.py      ← job count theo location + role
```

**Schema `fact_job_skills` (ví dụ):**

```python
# Từ Silver:
# job_id | skills (list) | normalized_role | seniority_level | salary_max | crawled_at

# Explode thành Gold:
# job_id | skill | normalized_role | seniority_level | salary_max | crawled_at | week
```

**Schema `agg_role_salary`:**

```python
# normalized_role | seniority_level | salary_median | salary_p25 | salary_p75 | job_count | week
```

---

### P3-2: Dashboard đọc trực tiếp từ Silver — không đúng vai trò các tầng

**File:** `dashboard/app.py`

```python
df = pd.read_parquet("data/silver/jobs_silver.parquet")
```

Dashboard thực hiện aggregation phức tạp (Counter, group-by, explode skills) trong session Streamlit. Mỗi user load page là một lần re-compute. Đây là công việc của Gold Layer.

**Đề xuất:** Sau khi có Gold, sửa dashboard:

```python
# Gold đã pre-computed
df_skills = pd.read_parquet("data/gold/fact_job_skills.parquet")
df_salary  = pd.read_parquet("data/gold/agg_role_salary.parquet")
```

---

### P3-3: Không có Bronze-level quality check

**Tình trạng:** Data Quality chỉ chạy sau transform (Silver). Bronze raw data không được kiểm tra gì trước khi xử lý.

**Hậu quả:** Nếu TopCV thay đổi HTML structure và crawler trả về empty/malformed records, pipeline vẫn chạy tiếp đến Silver trước khi phát hiện vấn đề. Lãng phí compute và khó debug.

**Đề xuất thêm `quality/bronze_check.py`:**

```python
def check_bronze(bronze_dir: Path) -> BronzeCheckResult:
    """Kiểm tra trước khi transform."""
    # 1. Các file bắt buộc có tồn tại?
    # 2. Tổng số records có trên ngưỡng tối thiểu?
    # 3. Tỷ lệ record có title/url hợp lệ?
    # 4. Timestamp crawl có trong 24h gần nhất?
```

Tích hợp vào `pipeline.py` trước bước merge:

```python
bronze_ok = check_bronze(bronze_dir)
if not bronze_ok.passed:
    logger.error(f"Bronze quality failed: {bronze_ok.reason}")
    return 1
```

---

### P3-4: Không có cơ chế deduplication xuyên suốt nhiều lần chạy

**Tình trạng:** `upsert_jobs()` trong crawler xử lý deduplicate trong một lần crawl. Nhưng không có cơ chế deduplicate khi chạy pipeline nhiều lần theo thời gian.

**Hậu quả:** Job A crawled ngày 1-6 và ngày 8-6 → xuất hiện 2 lần trong Silver, làm lệch count và salary stats.

**Đề xuất:** Trong `pipeline.py`, sau merge nhưng trước process:

```python
# Deduplicate by normalized_url, giữ record mới nhất
raw_records_df = pd.DataFrame(raw_records)
raw_records_df = raw_records_df.sort_values('crawled_at').drop_duplicates(
    subset=['normalized_url'], keep='last'
)
raw_records = raw_records_df.to_dict('records')
```

---

### P3-5: Source dữ liệu chỉ có TopCV — coverage hạn chế

**Tình trạng:** Tất cả crawlers đều target TopCV. `project.pdf` đề cập ITviec, VietnamWorks, LinkedIn nhưng không có trong implementation.

**Đề xuất kiến trúc multi-source:**

```
crawlers/src/
├── base_crawler.js          ← abstract class với interface chung
├── topcv/
│   ├── list-crawler.js
│   ├── detail-crawler.js
│   └── text-crawler.js
└── itviec/                  ← sprint tiếp theo
    ├── list-crawler.js
    └── detail-crawler.js
```

Cấu trúc này cho phép thêm source mới mà không đụng vào code cũ.

---

## 7. P4 — Production Readiness

> Không cần làm ngay nhưng cần trong roadmap để project thực sự professional.

---

### P4-1: Không có Docker / containerization

**Vấn đề:** Hiện tại setup yêu cầu Node.js + Python + uv được cài đúng version trên máy. Môi trường khác nhau → behavior khác nhau.

**Đề xuất `Dockerfile`:**

```dockerfile
FROM python:3.12-slim

# Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY . .
RUN uv sync && cd crawlers && npm install
```

**`docker-compose.yml`:**

```yaml
services:
  pipeline:
    build: .
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    command: uv run python cli.py run
```

---

### P4-2: Không có scheduling — pipeline phải chạy thủ công

**Vấn đề:** Để theo dõi xu hướng tuyển dụng theo thời gian, pipeline cần chạy định kỳ (hàng ngày/hàng tuần). Hiện tại hoàn toàn manual.

**Đề xuất (theo mức độ phức tạp):**

| Option | Complexity | Phù hợp khi |
|--------|-----------|-------------|
| Windows Task Scheduler / cron | Thấp | Local, personal use |
| APScheduler (Python) | Vừa | Muốn scheduling in-process |
| Airflow (Docker) | Cao | Muốn full orchestration + monitoring |

**Minimal implementation với APScheduler:**

```python
# scheduler.py
from apscheduler.schedulers.blocking import BlockingScheduler
from transform.src.orchestrator.pipeline import run_pipeline

scheduler = BlockingScheduler()

@scheduler.scheduled_job('cron', day_of_week='mon,wed,fri', hour=2)
def scheduled_pipeline():
    run_pipeline()

scheduler.start()
```

---

### P4-3: Không có `.env` support — không an toàn khi thêm credentials

**Vấn đề:** Khi thêm LinkedIn API key, database URL, hoặc webhook URL, hiện tại không có nơi nào để lưu secrets ngoài hardcode trong code hoặc `config.yaml` (sẽ bị commit lên git).

**Đề xuất:** Thêm `python-dotenv` vào dependencies, tạo `.env.example`:

```bash
# .env.example (commit lên git)
LINKEDIN_API_KEY=your_key_here
DATABASE_URL=postgresql://localhost:5432/datajobs
WEBHOOK_URL=

# .env (trong .gitignore — đã có)
LINKEDIN_API_KEY=actual_key
```

Trong `config_loader.py`:

```python
from dotenv import load_dotenv
load_dotenv()
```

---

### P4-4: Python pipeline không có file logging

**Vấn đề:** Crawler Node.js ghi log ra file (`crawl.log`, `crawl_detail.log`). Python pipeline chỉ log ra stdout. Không có lịch sử log để debug khi pipeline chạy scheduled.

**Đề xuất trong `main.py`:**

```python
import logging
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
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
```

---

### P4-5: Không có CI pipeline (GitHub Actions)

**Đề xuất `.github/workflows/ci.yml`:**

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: astral-sh/setup-uv@v3
        with:
          python-version: "3.12"
      
      - run: uv sync
      
      - name: Run unit tests
        run: uv run pytest transform/tests/unit/ -v
      
      - name: Run integration tests
        run: uv run pytest transform/tests/integration/ -v
```

---

### P4-6: Không có data versioning / snapshot strategy

**Vấn đề:** Khi chạy lại pipeline, `jobs_silver.parquet` bị overwrite. Không có cách nào so sánh Silver hôm nay với Silver tuần trước, không có rollback.

**Đề xuất đơn giản — date-partitioned Silver:**

```
data/silver/
├── 2026-06-19/
│   └── jobs_silver.parquet
├── 2026-06-20/
│   └── jobs_silver.parquet
└── latest -> 2026-06-20/  (symlink)
```

Hoặc thêm `run_date` column vào Silver để track:

```python
silver_job.run_date = datetime.today().date().isoformat()
```

---

## 8. Lộ trình triển khai theo Sprint

### Sprint 0 — Fix P0 ngay hôm nay (0.5 ngày)

| Task | File cần sửa | Effort |
|------|-------------|--------|
| Sửa `requires-python = ">=3.12"` | `pyproject.toml` | 1 min |
| Bỏ PowerShell trong `cli.py run` | `cli.py` | 30 min |
| Bỏ PowerShell trong `makefile` | `makefile` | 10 min |
| Pass `--format` vào transform | `cli.py`, `main.py` | 20 min |
| Move `import re` lên đầu file | `reader.py` | 2 min |
| Sửa README path dashboard | `README.md` | 2 min |
| Thêm `crawlers/node_modules/` vào `.gitignore` | `.gitignore` | 1 min |

---

### Sprint 1 — Fix P1 logic bugs (1–2 ngày)

| Task | File cần sửa | Effort |
|------|-------------|--------|
| `get_role_from_title()` return `None` thay vì default | `config.py` | 15 min |
| Fix `check_completeness()` không override param | `completeness.py` | 20 min |
| Mở rộng `LOCATION_MAPPING` với aliases | `config.py` | 1 giờ |
| Fix `timeliness.py` không mutate input df | `timeliness.py` | 20 min |
| Tách `typer` khỏi `runner.py` | `runner.py` | 30 min |
| Tách `COMPANY_NAMES_TO_FILTER` khỏi `STOPWORDS_VI` | `config.py` | 15 min |
| Fix docstring position trong `completeness.py` | `completeness.py` | 5 min |

---

### Sprint 2 — Code quality P2 (2–3 ngày)

| Task | Effort |
|------|--------|
| Xóa double `logging.basicConfig` | 5 min |
| Refactor `uniqueness.py` bỏ `iterrows()` | 1 giờ |
| Simplify `skills.py` — bỏ redundant token pass | 45 min |
| Điền nội dung `future.md`, `transform/README.md` | 1 giờ |
| Xóa `pyproject.toml` khỏi `.gitignore` | 2 min |

---

### Sprint 3 — Gold Layer (3–5 ngày)

| Task | Effort |
|------|--------|
| Tạo `transform/src/gold/` module | 1 ngày |
| `fact_job_skills.py` — explode skills | 2 giờ |
| `agg_role_salary.py` — salary stats | 2 giờ |
| `agg_skill_demand.py` — skill frequency | 2 giờ |
| Tích hợp Gold vào `pipeline.py` | 1 giờ |
| Sửa dashboard đọc từ Gold | 2 giờ |
| CLI command `cli.py gold` | 1 giờ |

---

### Sprint 4 — Production hardening (1 tuần)

| Task | Effort |
|------|--------|
| Bronze quality check | 1 ngày |
| Deduplication xuyên suốt nhiều runs | 3 giờ |
| File logging cho Python pipeline | 2 giờ |
| `.env` + `python-dotenv` | 1 giờ |
| `Dockerfile` + `docker-compose.yml` | 1 ngày |
| GitHub Actions CI | 2 giờ |
| Date-partitioned Silver snapshot | 2 giờ |

---

### Sprint 5 — Mở rộng source dữ liệu (1–2 tuần)

| Task | Effort |
|------|--------|
| Refactor crawlers thành `base_crawler.js` | 1 ngày |
| ITviec crawler (list + detail) | 2–3 ngày |
| `source` field routing trong transform | 2 giờ |
| Update quality checks cho multi-source | 2 giờ |

---

## 9. Ma trận đánh giá tổng thể

| Dimension | Điểm hiện tại | Điểm sau Sprint 2 | Điểm sau Sprint 4 |
|-----------|:---:|:---:|:---:|
| **Correctness** (code chạy đúng) | 5/10 | 9/10 | 9/10 |
| **Architecture** (thiết kế các tầng) | 7/10 | 7/10 | 9/10 |
| **Maintainability** (dễ sửa, dễ đọc) | 6/10 | 8/10 | 9/10 |
| **Observability** (log, report, alert) | 6/10 | 7/10 | 9/10 |
| **Portability** (chạy được nhiều OS) | 4/10 | 8/10 | 10/10 |
| **Test coverage** | 7/10 | 8/10 | 8/10 |
| **Production readiness** | 3/10 | 5/10 | 8/10 |
| **Data quality rigor** | 7/10 | 9/10 | 9/10 |

---

> **Tóm lại:** Project có nền tảng kiến trúc tốt và tư duy data engineering đúng hướng. Sprint 0 và Sprint 1 (tổng cộng khoảng 3–4 ngày) sẽ đưa project từ "hoạt động được trên máy tôi" lên "đúng hành vi, đúng logic". Sprint 3 (Gold Layer) là bước tạo ra giá trị analytics thực sự. Sprint 4 là bước để đặt project này vào CV với sự tự tin.
