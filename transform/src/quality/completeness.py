"""
completeness.py - Giai đoạn 1: Kiểm tra tính đầy đủ (Completeness)
==============================================================

Kiểm tra tỷ lệ dữ liệu bị thiếu (null/empty) ở các trường quan trọng.
Các trường kiểm tra:
- title, company, location_clean, normalized_role
- salary_min, salary_max, skills, deadline
"""

import pandas as pd
import numpy as np
from typing import Dict, Any


def _has_value(x) -> bool:
    """
    Kiểm tra xem một giá trị có "có dữ liệu" hay không.
    Hỗ trợ các kiểu: list, tuple, numpy.ndarray, str, và các kiểu khác.
    """
    if isinstance(x, (list, tuple, np.ndarray)):
        return len(x) > 0
    if isinstance(x, str):
        return x.strip() not in ('', '[]', 'None')
    return pd.notna(x)


def check_completeness(
    df: pd.DataFrame,
    warning_threshold: float = 0.95,
    error_threshold: float = 0.80,
    field_error_thresholds: Dict[str, float] = None
) -> Dict[str, Dict[str, Any]]:
    if field_error_thresholds is None:
        field_error_thresholds = {}
    """
    Kiểm tra tính đầy đủ của các trường quan trọng.
    Có thể điều chỉnh ngưỡng riêng cho từng trường bằng cách truyền
    field_error_thresholds vào tham số (sẽ triển khai sau).
    """

    if df.empty:
        return {}

    total_rows = len(df)

    # Định nghĩa ngưỡng lỗi riêng cho từng trường (override error_threshold chung)
    # Chỉ cần override cho những trường đặc biệt
    field_error_thresholds = {
        'salary_min': 0.25,   # 50% -> thay vì 80%
        'salary_max': 0.25,
    }

    fields = {
        'title': {
            'condition': lambda s: s.notna() & (s != '') & (s.str.strip() != '')
        },
        'company': {
            'condition': lambda s: s.notna() & (s != '') & (s.str.strip() != '')
        },
        'location_clean': {
            'condition': lambda s: s.notna() & (s != '') & (s.str.strip() != '')
        },
        'normalized_role': {
            'condition': lambda s: s.notna() & (s != '') & (s.str.strip() != '')
        },
        'salary_min': {
            'condition': lambda s: s.notna()
        },
        'salary_max': {
            'condition': lambda s: s.notna()
        },
        'skills': {
            'condition': lambda s: s.notna() & s.apply(_has_value)
        },
        'deadline': {
            'condition': lambda s: s.notna()
        }
    }

    results = {}

    for field, config in fields.items():
        if field not in df.columns:
            count = 0
        else:
            condition = config['condition'](df[field])
            count = condition.sum() if hasattr(condition, 'sum') else 0

        percentage = (count / total_rows) * 100 if total_rows > 0 else 0.0

        # Sử dụng ngưỡng lỗi riêng cho trường nếu có, nếu không dùng giá trị chung
        current_error = field_error_thresholds.get(field, error_threshold)

        if percentage >= warning_threshold * 100:
            status = 'OK'
        elif percentage >= current_error * 100:
            status = 'WARNING'
        else:
            status = 'ERROR'

        results[field] = {
            'count': int(count),
            'total': total_rows,
            'percentage': round(percentage, 2),
            'status': status
        }

    return results