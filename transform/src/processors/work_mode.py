"""
work_mode.py - Xác định hình thức làm việc
"""
from typing import Optional, Tuple
from ..utils.config import get_work_mode_from_text


def derive_work_mode(
    working_time: Optional[str],
    description: Optional[str],
    requirements: Optional[str]
) -> Tuple[str, bool]:
    """
    Xác định work_mode và job_work_from_home từ các trường văn bản.

    Args:
        working_time: Lịch làm việc chi tiết (từ detail)
        description: Mô tả công việc
        requirements: Yêu cầu ứng viên

    Returns:
        Tuple[str, bool]: (work_mode, job_work_from_home)
    """
    # 1. Gộp văn bản
    texts = []
    if working_time:
        texts.append(working_time)
    if description:
        texts.append(description)
    if requirements:
        texts.append(requirements)

    if not texts:
        return "Onsite", False

    full_text = " ".join(texts)

    # 2. Sử dụng hàm từ config
    return get_work_mode_from_text(full_text)


# ===== TEST =====
if __name__ == "__main__":
    test_cases = [
        ("Thứ 2 - Thứ 6 (từ 08:30 đến 18:00)", "", "", ("Onsite", False)),
        ("Làm việc từ xa, Remote", "", "", ("Remote", True)),
        ("Hybrid làm việc", "", "", ("Hybrid", True)),
        ("", "Remote work available", "", ("Remote", True)),
        ("", "", "Work from home", ("Remote", True)),
        ("Onsite tại văn phòng", "", "", ("Onsite", False)),
        ("", "", "", ("Onsite", False)),
    ]
    for working, desc, req, expected in test_cases:
        result = derive_work_mode(working, desc, req)
        status = "✓" if result == expected else "✗"
        print(f"{status} derive_work_mode() -> {result} (expected: {expected})")