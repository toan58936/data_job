"""
source_normalizer.py - Chuẩn hóa dữ liệu từ các nguồn về Bronze Contract
Input: raw record từ TopCV hoặc ITviec + source name
Output: dict chuẩn hóa với các trường cốt lõi cho transform
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def normalize_topcv(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chuẩn hóa record từ TopCV.
    
    TopCV schema:
        - id: str
        - title: str
        - company: str
        - location: str
        - salary: str
        - experience: str
        - url: str
        - normalized_url: str
        - deadline: str
        - level: str
        - number_of_hires: int
        - job_type: str
        - working_time: str
        - location_detail: str
        - description: str
        - requirements: str
        - benefits: str
        - crawled_at: str
        - original_title: str
    """
    return {
        # === IDENTIFIERS ===
        "source": "topcv",
        "job_id": record.get("id"),
        "job_url": record.get("url") or record.get("normalized_url"),

        # === CORE FIELDS ===
        "title": record.get("title"),
        "company": record.get("company"),
        "location_raw": record.get("location"),

        # === SALARY ===
        "salary_raw": record.get("salary"),
        "salary_pre_parsed": None,  # TopCV không có pre-parsed salary

        # === EXPERIENCE ===
        "experience_raw": record.get("experience"),

        # === SKILLS ===
        "skills_pre_extracted": None,  # TopCV không có pre-extracted skills

        # === TEXT CONTENT ===
        "description": record.get("description"),
        "requirements": record.get("requirements"),
        "benefits": record.get("benefits"),

        # === METADATA ===
        "crawled_at": record.get("crawled_at"),
        "deadline": record.get("deadline"),
        "level": record.get("level"),
        "number_of_hires": record.get("number_of_hires"),
        "job_type": record.get("job_type"),
        "working_time": record.get("working_time"),
        "location_detail": record.get("location_detail"),
        "original_title": record.get("original_title"),

        # === ITVIEC-SPECIFIC FIELDS (để NULL cho TopCV) ===
        "salary_source": None,
        "salary_hidden": None,
        "is_negotiable": False,
        "currency": None,
        "unit": None,
        "work_model": None,
    }


def normalize_itviec(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chuẩn hóa record từ ITviec.
    
    ITviec schema (từ listing + detail):
        - job_id: str (itviec_slug)
        - source: str (ITviec)
        - job_url: str
        - job_title: str
        - company_name: str
        - location: str
        - work_model: str (Onsite/Hybrid/Remote/At office)
        - salary_hidden: bool
        - skills: list[str]
        - posted_text: str
        - collected_at: str
        - salary_text: str
        - salary_min: float
        - salary_max: float
        - currency: str (USD/VND)
        - unit: str (MONTH/YEAR/HOUR)
        - salary_source: str (json-ld/html-label/...)
        - isNegotiable: bool
        - description: str
        - requirements: str
        - benefits: str
        - experience: str
        - detail_crawled_at: str
    """
    # Xử lý salary pre-parsed
    salary_pre = None
    if record.get("salary_min") is not None or record.get("salary_max") is not None:
        salary_pre = {
            "min": record.get("salary_min"),
            "max": record.get("salary_max"),
            "currency": record.get("currency"),
            "unit": record.get("unit"),
            "is_negotiable": record.get("isNegotiable", False),
        }

    # Xử lý skills pre-extracted
    skills_pre = record.get("skills")
    if not isinstance(skills_pre, list) or len(skills_pre) == 0:
        skills_pre = None

    return {
        # === IDENTIFIERS ===
        "source": "itviec",
        "job_id": record.get("job_id"),
        "job_url": record.get("job_url"),

        # === CORE FIELDS ===
        "title": record.get("job_title"),
        "company": record.get("company_name"),
        "location_raw": record.get("location"),

        # === SALARY ===
        "salary_raw": record.get("salary_text"),
        "salary_pre_parsed": salary_pre,

        # === EXPERIENCE ===
        "experience_raw": record.get("experience"),

        # === SKILLS ===
        "skills_pre_extracted": skills_pre,

        # === TEXT CONTENT ===
        "description": record.get("description"),
        "requirements": record.get("requirements"),
        "benefits": record.get("benefits"),

        # === METADATA ===
        "crawled_at": record.get("collected_at") or record.get("detail_crawled_at"),
        "deadline": None,  # ITviec không có deadline rõ ràng
        "level": None,
        "number_of_hires": None,
        "job_type": None,
        "working_time": None,
        "location_detail": None,
        "original_title": record.get("job_title"),

        # === ITVIEC-SPECIFIC FIELDS ===
        "salary_source": record.get("salary_source"),
        "salary_hidden": record.get("salary_hidden", False),
        "is_negotiable": record.get("isNegotiable", False),
        "currency": record.get("currency"),
        "unit": record.get("unit"),
        "work_model": record.get("work_model"),
    }


def normalize_record(record: Dict[str, Any], source: str) -> Dict[str, Any]:
    """
    Hàm tổng: chuẩn hóa record từ bất kỳ nguồn nào về Bronze Contract.
    
    Args:
        record: Raw record từ file Bronze (jobs_all.json, jobs_detail.json, ...)
        source: Tên nguồn ('topcv' hoặc 'itviec')
    
    Returns:
        Dict[str, Any]: Record đã chuẩn hóa theo Bronze Contract.
    
    Raises:
        ValueError: Nếu source không được hỗ trợ.
    """
    if source == "topcv":
        return normalize_topcv(record)
    elif source == "itviec":
        return normalize_itviec(record)
    else:
        raise ValueError(f"Unsupported source: {source}")