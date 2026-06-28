"""
config.py - Cấu hình cho tầng transform
"""
import re
from typing import List, Dict, Tuple, Optional, Set

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
    # ============================================================
    # 1. PATTERN TIẾNG VIỆT (ưu tiên cao nhất)
    # ============================================================
    # Kỹ sư dữ liệu
    (r"(?i)kỹ\s*sư\s*dữ\s*liệu", "Data Engineer"),
    (r"(?i)kỹ\s*sư\s*data", "Data Engineer"),
    
    # Chuyên viên phân tích dữ liệu
    (r"(?i)chuyên\s*viên\s*phân\s*tích\s*dữ\s*liệu", "Data Analyst"),
    (r"(?i)nhân\s*viên\s*phân\s*tích\s*dữ\s*liệu", "Data Analyst"),
    (r"(?i)chuyên\s*viên\s*data\s*analyst", "Data Analyst"),
    (r"(?i)chuyên\s*viên\s*phân\s*tích\s*data", "Data Analyst"),
    
    # Khoa học dữ liệu
    (r"(?i)chuyên\s*viên\s*khoa\s*học\s*dữ\s*liệu", "Data Scientist"),
    (r"(?i)kỹ\s*sư\s*khoa\s*học\s*dữ\s*liệu", "Data Scientist"),
    
    # Kỹ sư AI
    (r"(?i)kỹ\s*sư\s*ai", "AI Engineer"),
    (r"(?i)kỹ\s*sư\s*trí\s*tuệ\s*nhân\s*tạo", "AI Engineer"),
    (r"(?i)chuyên\s*viên\s*ai", "AI Engineer"),
    
    # Kỹ sư machine learning
    (r"(?i)kỹ\s*sư\s*machine\s*learning", "ML Engineer"),
    (r"(?i)chuyên\s*viên\s*machine\s*learning", "ML Engineer"),
    
    # ============================================================
    # 2. COMPOUND TITLES & ROLE MỞ RỘNG
    # ============================================================
    # Data Engineer với các biến thể
    (r"(?i)data\s*(?:engineer|analyst|scientist)\s*/\s*(?:bi|analytics|platform)", "Data Engineer"),
    (r"(?i)senior\s*backends?\s*[-–]\s*data\s*platform", "Data Engineer"),
    (r"(?i)fullstack\s*\(?\s*data\s*team\s*\)?", "Data Engineer"),
    (r"(?i)data\s*platform\s*(?:engineer|developer)", "Data Platform Engineer"),
    
    # Data Architect & Solution
    (r"(?i)data\s*(?:architect|solution\s*architect)", "Data Architect"),
    (r"(?i)solution\s*architect\s*data", "Data Architect"),
    
    # ETL / Data Integration
    (r"(?i)etl\s*(?:developer|engineer|architect)", "ETL Developer"),
    (r"(?i)data\s*integration\s*(?:engineer|developer)", "ETL Developer"),
    
    # Analytics Engineer
    (r"(?i)analytics\s*engineer", "Analytics Engineer"),
    (r"(?i)data\s*analytics\s*engineer", "Analytics Engineer"),
    
    # BI / Business Intelligence
    (r"(?i)bi\s*(?:engineer|developer|analyst)", "BI Analyst"),
    (r"(?i)business\s*intelligence\s*(?:engineer|developer)", "BI Analyst"),
    
    # Data Quality / Data Governance
    (r"(?i)data\s*quality\s*(?:engineer|analyst|specialist)", "Data Quality Engineer"),
    (r"(?i)data\s*governance\s*(?:engineer|analyst)", "Data Governance Engineer"),
    
    # Database
    (r"(?i)database\s*(?:engineer|administrator|developer|dba)", "Database Engineer"),
    (r"(?i)db\s*(?:engineer|administrator)", "Database Engineer"),
    
    # Data Consultant
    (r"(?i)data\s*(?:solution\s*)?consultant", "Data Consultant"),
    (r"(?i)data\s*advisory", "Data Consultant"),
    
    # Data Manager
    (r"(?i)data\s*manager", "Data Manager"),
    (r"(?i)data\s*&\s*reporting\s*manager", "Data Manager"),
    
    # DataOps
    (r"(?i)data\s*ops", "DataOps Engineer"),
    (r"(?i)dataops\s*(?:engineer|developer)", "DataOps Engineer"),
    
    # ============================================================
    # 3. ROLE CHUẨN (pattern gốc)
    # ============================================================
    # Data Engineer
    (r"\bdata engineer\b", "Data Engineer"),
    # Data Analyst
    (r"\bdata analyst\b", "Data Analyst"),
    # Data Scientist
    (r"\bdata scientist\b", "Data Scientist"),
    # BI Analyst
    (r"\bbusiness intelligence\b|\bbi\b", "BI Analyst"),
    # ML Engineer
    (r"\bmachine learning\b|\bml\b", "ML Engineer"),
    # AI Engineer
    (r"\bai engineer\b|\bartificial intelligence\b", "AI Engineer"),
    # Database Engineer
    (r"\bdatabase engineer\b|\bdatabase administrator\b|\bdba\b", "Database Engineer"),
    # Data Architect
    (r"\bdata architect\b", "Data Architect"),
    # Data Platform Engineer
    (r"\bdata platform\b", "Data Platform Engineer"),
    # ETL Developer
    (r"\betl developer\b", "ETL Developer"),
    # DataOps
    (r"\bdata\s*ops\b", "DataOps Engineer"),
    # Analytics Engineer
    (r"\banalytics engineer\b", "Analytics Engineer"),
    
    # ============================================================
    # 4. FALLBACK (nếu có "data" trong title nhưng chưa match)
    # ============================================================
    # Khi có từ "data" hoặc "analytics" nhưng chưa match pattern nào,
    # đánh dấu là "Data Professional" (thay vì None)
    (r"\bdata\b", "Data Professional"),
    (r"\banalytics\b", "Data Professional"),
]

# ==================== 3. MAPPING ĐỊA ĐIỂM ====================
LOCATION_MAPPING: Dict[str, str] = {
    # ==================== HÀ NỘI ====================
    "hà nội (mới)": "Hà Nội",
    "ha noi (new)": "Hà Nội",
    "hanoi (new)": "Hà Nội",
    "hà nội": "Hà Nội",
    "ha noi": "Hà Nội",
    "hanoi": "Hà Nội",
    "hn": "Hà Nội",
    "thủ đô": "Hà Nội",

    # ==================== HỒ CHÍ MINH ====================
    "hồ chí minh (mới)": "Hồ Chí Minh",
    "ho chi minh (new)": "Hồ Chí Minh",
    "thành phố hồ chí minh": "Hồ Chí Minh",
    "tp.hồ chí minh": "Hồ Chí Minh",
    "tp hồ chí minh": "Hồ Chí Minh",
    "hồ chí minh": "Hồ Chí Minh",
    "ho chi minh": "Hồ Chí Minh",
    "tp.hcm": "Hồ Chí Minh",
    "tp hcm": "Hồ Chí Minh",
    "hcm": "Hồ Chí Minh",
    "sài gòn": "Hồ Chí Minh",
    "saigon": "Hồ Chí Minh",

    # ==================== ĐÀ NẴNG ====================
    "đà nẵng (mới)": "Đà Nẵng",
    "da nang (new)": "Đà Nẵng",
    "đà nẵng": "Đà Nẵng",
    "da nang": "Đà Nẵng",
    "danang": "Đà Nẵng",

    # ==================== HẢI PHÒNG ====================
    "hải phòng (mới)": "Hải Phòng",
    "hai phong (new)": "Hải Phòng",
    "hải phòng": "Hải Phòng",
    "hai phong": "Hải Phòng",
    "haiphong": "Hải Phòng",
    "hp": "Hải Phòng",

    # ==================== CẦN THƠ ====================
    "cần thơ (mới)": "Cần Thơ",
    "can tho (new)": "Cần Thơ",
    "cần thơ": "Cần Thơ",
    "can tho": "Cần Thơ",
    "cantho": "Cần Thơ",
    "ct": "Cần Thơ",

    # ==================== BÌNH DƯƠNG ====================
    "bình dương (mới)": "Bình Dương",
    "binh duong (new)": "Bình Dương",
    "bình dương": "Bình Dương",
    "binh duong": "Bình Dương",

    # ==================== ĐỒNG NAI ====================
    "đồng nai (mới)": "Đồng Nai",
    "dong nai (new)": "Đồng Nai",
    "đồng nai": "Đồng Nai",
    "dong nai": "Đồng Nai",

    # ==================== BÀ RỊA - VŨNG TÀU ====================
    "bà rịa - vũng tàu": "Bà Rịa - Vũng Tàu",
    "ba ria - vung tau": "Bà Rịa - Vũng Tàu",
    "vũng tàu": "Bà Rịa - Vũng Tàu",
    "vung tau": "Bà Rịa - Vũng Tàu",

    # ==================== QUẢNG NINH ====================
    "quảng ninh": "Quảng Ninh",
    "quang ninh": "Quảng Ninh",

    # ==================== KHÁNH HÒA ====================
    "khánh hòa": "Khánh Hòa",
    "khanh hoa": "Khánh Hòa",

    # ==================== HƯNG YÊN ====================
    "hưng yên": "Hưng Yên",
    "hung yen": "Hưng Yên",

    # ==================== BẮC NINH ====================
    "bắc ninh": "Bắc Ninh",
    "bac ninh": "Bắc Ninh",

    # ==================== VĨNH PHÚC ====================
    "vĩnh phúc": "Vĩnh Phúc",
    "vinh phuc": "Vĩnh Phúc",

    # ==================== HẢI DƯƠNG ====================
    "hải dương": "Hải Dương",
    "hai duong": "Hải Dương",

    # ==================== THÁI NGUYÊN ====================
    "thái nguyên": "Thái Nguyên",
    "thai nguyen": "Thái Nguyên",

    # ==================== PHÚ THỌ ====================
    "phú thọ": "Phú Thọ",
    "phu tho": "Phú Thọ",

    # ==================== NGHỆ AN ====================
    "nghệ an": "Nghệ An",
    "nghe an": "Nghệ An",

    # ==================== THANH HÓA ====================
    "thanh hóa": "Thanh Hóa",
    "thanh hoa": "Thanh Hóa",
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
    'kho', 'chieu', 'thu', 'ban', 'tranh', 'cung', 'tinh', 'chinh', 'nhu',
}

COMPANY_NAMES_TO_FILTER: Set[str] = {
    'viettel',
    'cmc',
    'fpt',
    'vpbank',
    'techcombank',
    'vietinbank',
    'agribank',
    'bidv',
}
# ==================== 7. HÀM TIỆN ÍCH CHO CONFIG ====================
def get_role_from_title(title: str) -> Optional[str]:
    """
    Duyệt qua ROLE_MAPPING, trả về role chuẩn đầu tiên khớp.
    Nếu không khớp bất kỳ pattern nào, trả về None.
    """
    title_lower = title.lower()
    for pattern, role in ROLE_MAPPING:
        if re.search(pattern, title_lower):
            return role
    # Fallback: nếu title chứa "data" hoặc "analytics" -> Unclassified
    if re.search(r'\bdata\b|\banalytics\b', title_lower):
        return "Data Professional"
    return None

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