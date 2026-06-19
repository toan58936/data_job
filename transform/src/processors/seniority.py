"""
seniority.py - Xác định cấp bậc kinh nghiệm
"""
from typing import Optional
from ..utils.config import get_seniority_from_title_and_exp



def derive_seniority(title: Optional[str], exp_min: Optional[int]) -> Optional[str]:
    """
    Xác định seniority_level từ title và exp_min.

    Args:
        title: Tiêu đề job
        exp_min: Kinh nghiệm tối thiểu (năm)

    Returns:
        str: Junior / Middle / Senior / Lead / Unknown / None
    """
    if not title and exp_min is None:
        return None

    return get_seniority_from_title_and_exp(title or "", exp_min)


# ===== TEST =====
if __name__ == "__main__":
    test_cases = [
        ("Senior Data Engineer", 5, "Senior"),
        ("Junior Developer", 1, "Junior"),
        ("Data Engineer", 3, "Middle"),
        ("Lead Engineer", 7, "Lead"),
        ("Data Engineer", 0, "Junior"),
        ("Data Engineer", 2, "Middle"),
        ("Data Engineer", 5, "Senior"),
        ("Data Engineer", 8, "Lead"),
        ("", None, None),
    ]
    for title, exp, expected in test_cases:
        result = derive_seniority(title, exp)
        status = "✓" if result == expected else "✗"
        print(f"{status} derive_seniority({title!r}, {exp}) -> {result!r} (expected: {expected!r})")