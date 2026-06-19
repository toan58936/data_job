"""
config.py - Cấu hình cho tầng transform
"""
import re
from typing import List, Dict, Tuple

# ==================== 1. DANH SÁCH KỸ NĂNG ====================
# Các từ khóa kỹ năng phổ biến trong ngành Data (Tiếng Anh và Tiếng Việt)
SKILL_KEYWORDS: List[str] = [
    # Ngôn ngữ lập trình & truy vấn
    "python", "sql", "java", "scala", "c++", "c#", "javascript", "typescript",
    "bash", "shell", "powershell", "rust", "go", "ruby", "php", "r", "excel",
    "git", "linux",

    # Hệ quản trị CSDL
    "postgresql", "mysql", "oracle", "sql server", "mongodb", "redis", "elasticsearch",
    "cassandra", "dynamodb", "neo4j", "hbase", "couchbase", "mariadb", "sqlite",
    "memcached",

    # Nền tảng cloud
    "aws", "azure", "gcp", "google cloud", "amazon web services",
    "ec2", "s3", "lambda", "glue", "redshift", "athena", "kinesis", "emr", "rds",
    "bigquery", "dataproc", "dataflow", "pub/sub", "cloud storage",
    "cloudformation",

    # Big Data & Streaming
    "hadoop", "spark", "kafka", "flink", "storm", "hive", "pig", "sqoop", "hbase",
    "zookeeper", "hdfs", "yarn", "mapreduce", "presto", "trino", "kinesis",

    # ETL & Orchestration
    "airflow", "nifi", "talend", "informatica", "datastage", "pentaho",
    "ssis", "ssas", "dbt", "dagster", "prefect", "airbyte",

    # BI & Visualization
    "power bi", "tableau", "qlik", "looker", "metabase", "superset", "cognos",
    "microstrategy", "sisense", "thoughtspot",

    # DevOps & Infrastructure
    "docker", "kubernetes", "k8s", "terraform", "ansible", "jenkins", "gitlab ci",
    "github actions", "ci/cd", "helm", "istio", "prometheus", "grafana",
    "logstash", "kibana",

    # Data Science & ML
    "machine learning", "ml", "deep learning", "artificial intelligence",
    "nlp", "computer vision", "predictive modeling", "statistics", "linear regression",
    "logistic regression", "decision tree", "random forest", "xgboost", "tensorflow",
    "pytorch", "scikit-learn", "pandas", "numpy", "matplotlib", "seaborn",

    # Data Governance (chỉ giữ các công cụ cụ thể)
    "datahub", "openmetadata",

    # Các công nghệ khác
    "api", "rest api", "graphql", "microservices", "event-driven", "message queue",
    "rabbitmq", "activemq", "pub/sub", "streaming", "batch processing",
    "real-time", "near real-time",

    # Nền tảng doanh nghiệp
    "sap", "sap bw",
]
# ==================== 2. MAPPING VAI TRÒ (ROLE) ====================
# Danh sách các role chuẩn theo thứ tự ưu tiên (khớp đầu tiên)
# Sử dụng \b để khớp chính xác từ (không bị match sub-word)
ROLE_MAPPING: List[Tuple[str, str]] = [
    (r"\bdata engineer\b", "Data Engineer"),
    (r"\bdata analyst\b", "Data Analyst"),
    (r"\bdata scientist\b", "Data Scientist"),
    (r"\bbusiness intelligence\b|\bbi\b", "BI Analyst"),
    (r"\bmachine learning\b|\bml\b", "ML Engineer"),
    (r"\bai engineer\b|\bartificial intelligence\b", "AI Engineer"),
    (r"\bdatabase engineer\b|\bdatabase administrator\b|\bdba\b", "Database Engineer"),
    (r"\bdata architect\b", "Data Architect"),
    (r"\bdata platform\b", "Data Platform Engineer"),
    (r"\betl developer\b", "ETL Developer"),
    (r"\bdata\s*ops\b", "DataOps Engineer"),
    (r"\banalytics engineer\b", "Analytics Engineer"),
]

# ==================== 3. MAPPING ĐỊA ĐIỂM ====================
LOCATION_MAPPING: Dict[str, str] = {
    "Hà Nội": "Hà Nội",
    "Hồ Chí Minh": "Hồ Chí Minh",
    "Đà Nẵng": "Đà Nẵng",
    "Hải Phòng": "Hải Phòng",
    "Cần Thơ": "Cần Thơ",
    "Bình Dương": "Bình Dương",
    "Đồng Nai": "Đồng Nai",
    "Bà Rịa - Vũng Tàu": "Bà Rịa - Vũng Tàu",
    "Quảng Ninh": "Quảng Ninh",
    "Khánh Hòa": "Khánh Hòa",
    "Hưng Yên": "Hưng Yên",
    "Bắc Ninh": "Bắc Ninh",
    "Vĩnh Phúc": "Vĩnh Phúc",
    "Hải Dương": "Hải Dương",
    "Thái Nguyên": "Thái Nguyên",
    "Phú Thọ": "Phú Thọ",
    "Nghệ An": "Nghệ An",
    "Thanh Hóa": "Thanh Hóa",
}

# ==================== 4. QUY TẮC SENIORITY ====================
# Từ khóa trong title -> seniority level (sử dụng \b để khớp chính xác)
SENIORITY_KEYWORDS: Dict[str, str] = {
    r"\bsenior\b": "Senior",
    r"\blead\b": "Lead",
    r"\bprincipal\b": "Principal",
    r"\bstaff\b": "Staff",
    r"\bjunior\b": "Junior",
    r"\bmiddle\b": "Middle",
    r"\bfresher\b": "Fresher",
    r"\bintern\b": "Intern",
}

# Quy tắc dựa trên kinh nghiệm (năm)
EXP_TO_SENIORITY: List[Tuple[int, int, str]] = [
    (0, 1, "Junior"),      # 0-1 năm
    (2, 3, "Middle"),      # 2-3 năm
    (4, 6, "Senior"),      # 4-6 năm
    (7, 100, "Lead"),      # >=7 năm
]

# ==================== 5. QUY TẮC WORK MODE ====================
WORK_MODE_KEYWORDS = {
    "remote": ("Remote", True),
    "work from home": ("Remote", True),
    "wfh": ("Remote", True),
    "hybrid": ("Hybrid", True),
    "onsite": ("Onsite", False),
    "on-site": ("Onsite", False),
    "tại văn phòng": ("Onsite", False),
}

# ==================== 6. JOB SCHEDULE TYPE ====================
JOB_SCHEDULE_MAPPING = {
    "Toàn thời gian": "Full-time",
    "Full-time": "Full-time",
    "Bán thời gian": "Part-time",
    "Part-time": "Part-time",
    "Thực tập": "Internship",
    "Internship": "Internship",
}

DOMAIN_KEYWORDS: List[str] = [
    # Kiến trúc dữ liệu (chỉ giữ cụm dài nhất)
    "data warehouse",
    "data lakehouse",
    "data mesh",
    "data fabric",
    "data federation",
    # Quản trị & Chất lượng
    "data governance",
    "data quality",
    "data lineage",
    "metadata management",
    "data catalog",
    "data observability",
    "data profiling",
    "data validation",
    "master data management",
    "mdm",
    # Mô hình xử lý
    "batch processing",
    "real-time",           # giữ real-time, bỏ "streaming" để tránh trùng
    "near real-time",
    "lambda architecture",
    "kappa architecture",
    # Lĩnh vực
    "fintech",
    "loyalty",
    "ecommerce",
    "banking",
    "airline",
    "logistics",
    "genai",
    "llm",
    "machine learning",
    "ai",
]
STOPWORDS_VI = {
    # Đại từ, liên từ, giới từ
    'và', 'hoặc', 'với', 'cho', 'của', 'từ', 'đến', 'trong', 'ngoài', 'trên', 'dưới',
    'theo', 'qua', 'bằng', 'được', 'có', 'không', 'cũng', 'đã', 'sẽ', 'đang', 'là', 'ở',
    'tại', 'về', 'như', 'nên', 'bởi', 'vì', 'do', 'mà',
    # Động từ chung
    'làm', 'thực hiện', 'xây dựng', 'phát triển', 'tham gia', 'hỗ trợ', 'đảm bảo',
    'quản lý', 'tối ưu', 'thiết kế', 'triển khai', 'vận hành', 'giám sát', 'kiểm tra',
    'đánh giá', 'báo cáo', 'nghiên cứu', 'học hỏi', 'cải thiện', 'điều phối', 'phối hợp',
    'tích hợp', 'đồng bộ', 'chuẩn hóa', 'làm sạch', 'xử lý', 'phân tích', 'tổ chức',
    'lưu trữ', 'bảo mật', 'đào tạo', 'hướng dẫn', 'tư vấn', 'đề xuất', 'lập kế hoạch',
    # Danh từ chung
    'kinh nghiệm', 'yêu cầu', 'kỹ năng', 'công việc', 'vị trí', 'ứng viên', 'doanh nghiệp',
    'hệ thống', 'dữ liệu', 'mô hình', 'quy trình', 'dự án', 'nhóm', 'bộ phận', 'phòng ban',
    'công ty', 'tập đoàn', 'ngân hàng', 'tài chính', 'bảo hiểm', 'thương mại', 'điện tử',
    'viễn thông', 'công nghệ', 'thông tin', 'khoa học', 'máy tính', 'phần mềm', 'ứng dụng',
    'sản phẩm', 'dịch vụ', 'khách hàng', 'đối tác', 'giải pháp', 'nền tảng', 'hạ tầng',
    # Từ chỉ số lượng, thời gian
    'năm', 'tháng', 'ngày', 'giờ', 'lần', 'hơn', 'ít', 'khoảng', 'tối thiểu', 'tối đa',
    'trung bình', 'thường', 'mới', 'cũ', 'cũng',
    # Các từ khác
    'ví dụ', 'như sau', 'sau đây', 'tuy nhiên', 'đồng thời', 'thêm vào đó',
    # Thêm các từ xuất hiện nhiều trong skill_candidates.txt
    'nghi', 'thi', 'tri', 'quy', 'ngh', 'chuy', 'tuy', 'thu', 'gia', 'danh', 'huy', 'tra',
    'minh', 'vai', 'chung', 'trung', 'thao', 'thuy', 'tho', 'tinh', 'nghe', 'lao', 'nguy',
    'sau', 'khi', 'ngu', 'bao', 'sinh', 'nam', 'doanh', 'truy', 'duy', 'thanh', 'linh',
    'kho', 'chieu', 'thu', 'ban', 'tranh', 'cung', 'tinh', 'chinh', 'nhu', 'viettel',
    'cmc', 'fpt', 'vpbank', 'techcombank', 'vietinbank', 'agribank', 'bidv',
}
# ==================== 7. HÀM TIỆN ÍCH CHO CONFIG ====================
def get_role_from_title(title: str) -> str:
    """Duyệt qua ROLE_MAPPING, trả về role chuẩn đầu tiên khớp, hoặc 'Data Engineer' nếu không khớp."""
    title_lower = title.lower()
    for pattern, role in ROLE_MAPPING:
        if re.search(pattern, title_lower):
            return role
    return "Data Engineer"  # Mặc định

def get_seniority_from_title_and_exp(title: str, exp_min: int) -> str:
    """
    Xác định seniority dựa trên từ khóa trong title và exp_min.
    Ưu tiên từ khóa trong title trước, nếu không có thì dựa trên exp_min.
    """
    title_lower = title.lower()
    for pattern, level in SENIORITY_KEYWORDS.items():
        if re.search(pattern, title_lower):
            return level
    # Nếu không có từ khóa, dựa vào exp_min
    if exp_min is not None:
        for low, high, level in EXP_TO_SENIORITY:
            if low <= exp_min <= high:
                return level
    return "Unknown"

def get_work_mode_from_text(text: str) -> Tuple[str, bool]:
    """
    Tìm từ khóa work mode trong chuỗi văn bản (working_time, description).
    Trả về (work_mode, job_work_from_home).
    Mặc định: Onsite, False.
    """
    text_lower = text.lower()
    for keyword, (mode, wfh) in WORK_MODE_KEYWORDS.items():
        if keyword in text_lower:
            return mode, wfh
    return "Onsite", False