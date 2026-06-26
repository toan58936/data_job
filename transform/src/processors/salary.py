"""
salary.py - Chuẩn hóa lương
Hỗ trợ cả lương thô (parse từ text) và lương đã được pre-parsed (từ ITviec)
"""

import re
from typing import Optional, Dict, Any


def parse_salary(
    raw_salary: Optional[str],
    pre_parsed: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Parse hoặc trả về lương đã được xử lý sẵn.

    Args:
        raw_salary: Chuỗi lương thô (dùng cho TopCV hoặc fallback)
        pre_parsed: Dict chứa lương đã parse sẵn (từ ITviec), có các key:
            - min: float
            - max: float
            - currency: str (VND/USD)
            - unit: str (MONTH/YEAR/HOUR)
            - is_negotiable: bool

    Returns:
        Dict: {
            'salary_min': float or None,
            'salary_max': float or None,
            'currency': str or None,
            'is_negotiable': bool
        }
    """
    # Ưu tiên pre-parsed nếu có
    if pre_parsed and pre_parsed.get('min') is not None:
        return {
            'salary_min': pre_parsed['min'],
            'salary_max': pre_parsed['max'],
            'currency': pre_parsed.get('currency') or 'VND',
            'is_negotiable': pre_parsed.get('is_negotiable', False)
        }

    # Fallback: parse từ raw text
    if not raw_salary:
        return {
            'salary_min': None,
            'salary_max': None,
            'currency': None,
            'is_negotiable': False
        }

    salary = raw_salary.strip()

    # 1. Trường hợp "Thoả thuận" hoặc "Negotiable"
    if re.search(r'thoả thuận|thương lượng|negotiable|négociable', salary, re.IGNORECASE):
        return {
            'salary_min': None,
            'salary_max': None,
            'currency': None,
            'is_negotiable': True
        }

    # 2. Xác định đơn vị tiền tệ
    currency = "VND"  # mặc định
    if "usd" in salary.lower():
        currency = "USD"
    elif "vnd" in salary.lower():
        currency = "VND"

    # 3. Làm sạch chuỗi: loại bỏ các từ không cần thiết, giữ lại số, dấu gạch ngang, dấu phẩy
    clean = re.sub(r'thưởng|bonus|upto|up to|~|khoảng|tr\.|triệu|đồng|\$', '', salary, flags=re.IGNORECASE)
    clean = re.sub(r'[^0-9,.\-–—]', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()

    # 4. Tìm các số trong chuỗi
    numbers = re.findall(r'([\d,]+\.?\d*)', clean)
    if not numbers:
        # Không có số nào
        # Thử với pattern đặc biệt "Tới X"
        match = re.search(r'tới\s*([\d,]+)\s*(?:triệu|m|milion)?', salary, re.IGNORECASE)
        if match:
            val = float(match.group(1).replace(',', ''))
            if currency == "VND" and val > 1000:
                val = val / 1_000_000
            return {
                'salary_min': None,
                'salary_max': round(val, 1),
                'currency': currency,
                'is_negotiable': False
            }
        # Nếu không parse được, coi là thỏa thuận
        return {
            'salary_min': None,
            'salary_max': None,
            'currency': None,
            'is_negotiable': True
        }

    # 5. Chuyển đổi số thành float
    nums = [float(n.replace(',', '')) for n in numbers]

    # 6. Xác định min và max
    if len(nums) == 1:
        salary_min = None
        salary_max = nums[0]
    else:
        salary_min = min(nums)
        salary_max = max(nums)

    # 7. Chuyển đổi đơn vị: nếu VND và số > 1000, chia cho 1 triệu
    if currency == "VND":
        if salary_min and salary_min > 1000:
            salary_min = salary_min / 1_000_000
        if salary_max and salary_max > 1000:
            salary_max = salary_max / 1_000_000
    # USD giữ nguyên

    # 8. Làm tròn đến 1 chữ số thập phân
    if salary_min is not None:
        salary_min = round(salary_min, 1)
    if salary_max is not None:
        salary_max = round(salary_max, 1)

    return {
        'salary_min': salary_min,
        'salary_max': salary_max,
        'currency': currency if currency else None,
        'is_negotiable': False
    }