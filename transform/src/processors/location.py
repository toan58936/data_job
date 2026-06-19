"""
location.py - Chuẩn hóa địa điểm
"""
import re
from typing import Optional


def clean_location(raw_location: Optional[str]) -> Optional[str]:
    """
    Chuẩn hóa địa điểm từ raw.

    Args:
        raw_location: Chuỗi địa điểm thô

    Returns:
        str: Địa điểm đã chuẩn hóa, hoặc None nếu không có dữ liệu.
    """
    if not raw_location:
        return None

    location = raw_location.strip()

    # 1. Loại bỏ tiền tố "Việc làm tại "
    if location.startswith("Việc làm tại "):
        location = location.replace("Việc làm tại ", "")

    # 2. Xử lý nhiều địa điểm (lấy địa điểm đầu tiên)
    separators = [" & ", " | ", " / ", ", ", " - "]
    for sep in separators:
        if sep in location:
            location = location.split(sep)[0].strip()
            break

    # 3. Loại bỏ hậu tố (mới), (cũ)
    location = re.sub(r'\s*\([^)]*\)\s*', ' ', location).strip()

    # 4. Mapping từ config (nếu có)
    from ..utils.config import LOCATION_MAPPING
    for city, normalized in LOCATION_MAPPING.items():
        if city.lower() in location.lower():
            return normalized

    # 5. Fallback: giữ nguyên chuỗi đã làm sạch
    return location