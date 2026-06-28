"""
silver_schema.py - Định nghĩa schema cho tầng Silver
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class SilverJob:
    """Mô tả một bản ghi job đã được chuẩn hóa ở tầng Silver."""
    job_id: Optional[str] = None
    source: str = "TopCV"
    job_url: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location_raw: Optional[str] = None
    location_clean: Optional[str] = None
    salary_min: Optional[float] = None          # Triệu VND hoặc USD
    salary_max: Optional[float] = None
    currency: Optional[str] = None              # "VND" hoặc "USD"
    is_negotiable: bool = False
    exp_min: Optional[int] = None               # Năm kinh nghiệm
    exp_max: Optional[int] = None
    deadline: Optional[str] = None              # Định dạng YYYY-MM-DD
    level: Optional[str] = None                 # Cấp bậc tuyển dụng (Nhân viên, Trưởng nhóm,...)
    number_of_hires: Optional[int] = None
    job_schedule_type: Optional[str] = None     # Full-time / Part-time / Internship
    working_time: Optional[str] = None          # Lịch làm việc chi tiết
    job_country: str = "Vietnam"
    work_mode: str = "Onsite"                   # Onsite / Hybrid / Remote
    job_work_from_home: bool = False
    seniority_level: Optional[str] = None       # Junior / Middle / Senior / Lead
    normalized_role: Optional[str] = None       # Data Engineer, Data Analyst, ...
    skills: List[str] = field(default_factory=list)
    domain_keywords: List[str] = field(default_factory=list)   # <-- THÊM MỚI
    salary_source_type: Optional[str] = None    # explicit / negotiable / hidden / not_found
    salary_hidden: bool = False                 # ITviec: lương bị ẩn bởi platform
    description: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    crawled_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SilverJob":
        """
        Tạo instance SilverJob từ dict, bỏ qua các trường không khớp.
        Chuyển đổi crawled_at thành datetime nếu là string.
        """
        # Xử lý crawled_at
        crawled = data.get("crawled_at")
        if isinstance(crawled, str):
            try:
                crawled = datetime.fromisoformat(crawled.replace("Z", "+00:00"))
            except ValueError:
                crawled = None

        # Lọc các trường khớp với dataclass
        field_names = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in field_names}
        filtered["crawled_at"] = crawled

        # Đảm bảo skills là list
        if "skills" in filtered and not isinstance(filtered["skills"], list):
            if isinstance(filtered["skills"], str):
                filtered["skills"] = [s.strip() for s in filtered["skills"].split(",") if s.strip()]
            else:
                filtered["skills"] = []

        return cls(**filtered)

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi instance thành dict, xử lý datetime."""
        result = self.__dict__.copy()
        if result.get("crawled_at") and isinstance(result["crawled_at"], datetime):
            result["crawled_at"] = result["crawled_at"].isoformat()
        return result