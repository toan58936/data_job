# transform/src/processors/domain.py
"""
domain.py - Trích xuất từ khóa lĩnh vực / kiến trúc
"""
import re
from typing import List, Optional


def extract_domain_keywords(
    title: Optional[str],
    description: Optional[str],
    requirements: Optional[str],
    domain_keywords: List[str]
) -> List[str]:
    """
    Trích xuất các từ khóa lĩnh vực/kiến trúc từ title, description, requirements.
    Sử dụng regex với boundary \b để khớp chính xác.
    """
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
    found = set()
    for keyword in domain_keywords:
        # Xử lý keyword có dấu cách hoặc không
        if " " in keyword:
            pattern = r'\b' + keyword.replace(" ", r'\s+') + r'\b'
        else:
            pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, full_text):
            found.add(keyword)

    return sorted(list(found))