"""
skills.py - Trích xuất kỹ năng từ văn bản (sử dụng Regex tổng hợp)
Hỗ trợ cả pre-extracted skills (từ ITviec) và extract từ text (TopCV)
"""

import re
from typing import List, Optional

from ..utils.config import SKILL_KEYWORDS, DOMAIN_KEYWORDS


def _make_pattern(keyword: str) -> str:
    """
    Tạo regex pattern cho một keyword, xử lý đúng cả 2 trường hợp:

    1. Keyword thông thường ('python', 'spark', 'ml'):
       Dùng lookaround (?<![a-zA-Z0-9]) ... (?![a-zA-Z0-9]) thay vì \b.
       Lý do: \b không hoạt động với keyword chứa ký tự đặc biệt như
       c++ hay c# (vì + và # là non-word char, \b bị hiểu sai boundary).
       Lookaround không phụ thuộc vào loại ký tự nên stable hơn.

    2. Keyword nhiều từ ('power bi', 'machine learning', 'rest api'):
       Split theo space, escape từng phần, nối bằng \\s+ để bắt được
       cả "Power  BI" hay "machine  learning" (nhiều space).
    """
    if " " in keyword:
        parts = keyword.split(" ")
        inner = r'\s+'.join(re.escape(p) for p in parts)
        return r'(?<![a-zA-Z0-9])' + inner + r'(?![a-zA-Z0-9])'
    else:
        return r'(?<![a-zA-Z0-9])' + re.escape(keyword) + r'(?![a-zA-Z0-9])'


def extract_skills(
    title: Optional[str],
    description: Optional[str],
    requirements: Optional[str],
    skill_keywords: List[str],
    pre_extracted: Optional[List[str]] = None
) -> List[str]:
    """
    Trích xuất danh sách kỹ năng từ title, description, requirements.
    Sử dụng regex để tìm kiếm trực tiếp các từ khóa kỹ năng trong văn bản.

    Args:
        title: Tiêu đề job
        description: Mô tả công việc
        requirements: Yêu cầu công việc
        skill_keywords: Danh sách các từ khóa kỹ năng cần tìm
        pre_extracted: Danh sách kỹ năng đã được trích xuất sẵn (từ ITviec)

    Returns:
        List[str]: Danh sách kỹ năng đã tìm thấy (đã sắp xếp)
    """
    # Ưu tiên pre_extracted nếu được truyền vào (kể cả empty list)
    if isinstance(pre_extracted, list):
        # Normalize và lọc
        skill_set = set(skill_keywords)
        domain_set = set(DOMAIN_KEYWORDS)
        normalized = set()
        for s in pre_extracted:
            s_lower = s.lower().strip()
            if s_lower in skill_set and s_lower not in domain_set:
                normalized.add(s_lower)
        return sorted(list(normalized))

    # Fallback: extract từ text (TopCV)
    # 1. Gộp văn bản
    texts = []
    if title:
        texts.append(title)
    if description:
        texts.append(description)
    if requirements:
        texts.append(requirements)

    if not texts:
        return []

    full_text = " ".join(texts).lower()

    # 2. Duyệt từng từ khóa, tìm kiếm bằng regex pattern
    found_skills = set()
    for keyword in skill_keywords:
        pattern = _make_pattern(keyword)
        if re.search(pattern, full_text):
            found_skills.add(keyword)

    # 3. Loại bỏ các kỹ năng trùng với DOMAIN_KEYWORDS
    domain_set = set(DOMAIN_KEYWORDS)
    found_skills = found_skills - domain_set

    # 4. Sắp xếp kết quả
    return sorted(list(found_skills))