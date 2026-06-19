"""
role.py - Chuẩn hóa vai trò
"""
from typing import Optional
from ..utils.config import get_role_from_title



def normalize_role(title: Optional[str]) -> Optional[str]:
    """
    Chuẩn hóa vai trò từ tiêu đề job.

    Args:
        title: Tiêu đề job (ví dụ: "Senior Data Engineer")

    Returns:
        str: Vai trò đã chuẩn hóa (ví dụ: "Data Engineer")
    """
    if not title:
        return None

    return get_role_from_title(title)


# ===== TEST =====
if __name__ == "__main__":
    test_cases = [
        ("Senior Data Engineer", "Data Engineer"),
        ("Data Analyst", "Data Analyst"),
        ("Machine Learning Engineer", "ML Engineer"),
        ("AI Engineer", "AI Engineer"),
        ("Data Engineer Lead", "Data Engineer"),
        ("Database Administrator", "Database Engineer"),
        ("Data Architect", "Data Architect"),
        ("ETL Developer", "ETL Developer"),
        ("Unknown Title", "Data Engineer"),  # Default
        ("", None),
        (None, None),
    ]
    for title, expected in test_cases:
        result = normalize_role(title)
        status = "✓" if result == expected else "✗"
        print(f"{status} normalize_role({title!r}) -> {result!r} (expected: {expected!r})")