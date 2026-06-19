"""
experience.py - Chuẩn hóa kinh nghiệm
"""
import re
from typing import Optional, Tuple


def parse_experience(raw_exp: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """
    Parse chuỗi kinh nghiệm thành (exp_min, exp_max).

    Args:
        raw_exp: Chuỗi kinh nghiệm thô (ví dụ: "3 năm", "Trên 5 năm")

    Returns:
        Tuple[int, int]: (exp_min, exp_max), các giá trị có thể là None.
    """
    if not raw_exp:
        return None, None

    exp = raw_exp.strip().lower()

    # 1. Trường hợp "Không yêu cầu" hoặc "Không"
    if re.search(r'không yêu cầu|không|none|no experience', exp):
        return 0, None

    # 2. Trường hợp "Trên X năm" -> (X, None)
    match = re.search(r'trên\s*(\d+(?:\.\d+)?)\s*năm', exp)
    if match:
        return int(float(match.group(1))), None

    # 3. Trường hợp "Dưới X năm" -> (0, X)
    match = re.search(r'dưới\s*(\d+(?:\.\d+)?)\s*năm', exp)
    if match:
        return 0, int(float(match.group(1)))

    # 4. Trường hợp "X - Y năm" hoặc "X-Y năm" -> (X, Y)
    match = re.search(r'(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)\s*(?:năm|year|yr)', exp)
    if match:
        return int(float(match.group(1))), int(float(match.group(2)))

    # 5. Trường hợp dải số không có đơn vị (ví dụ "2-3", "2 - 3") -> (X, Y)
    match = re.search(r'(\d+)\s*[-–—]\s*(\d+)', exp)
    if match:
        return int(match.group(1)), int(match.group(2))

    # 6. Trường hợp "X năm" hoặc "X+" -> (X, X) hoặc (X, None)
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:\+|trở lên|năm|year|yr)', exp)
    if match:
        val = int(float(match.group(1)))
        if '+' in exp or 'trở lên' in exp:
            return val, None
        return val, val

    # 7. Trường hợp chỉ có số (ví dụ "5")
    match = re.search(r'^(\d+(?:\.\d+)?)$', exp)
    if match:
        val = int(float(match.group(1)))
        return val, val

    # 8. Trường hợp "fresher" / "intern" -> (0, 0)
    if re.search(r'fresher|intern|mới ra trường', exp):
        return 0, 0

    # 9. Không parse được -> None
    return None, None