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
    """
    Kiểm tra tính đầy đủ của các trường quan trọng.

    Tham số:
        df: DataFrame đầu vào (Silver).
        warning_threshold: Ngưỡng tỷ lệ để đạt WARNING (mặc định 95%).
        error_threshold: Ngưỡng tỷ lệ để đạt ERROR (mặc định 80%).
        field_error_thresholds: Dict cho phép override error_threshold cho từng trường.
            Ví dụ: {'salary_min': 0.25, 'salary_max': 0.25}
    """
    # Khởi tạo field_error_thresholds nếu None
    if field_error_thresholds is None:
        field_error_thresholds = {}

    # Default overrides cho các trường đặc biệt (ưu tiên thấp hơn)
    default_overrides = {
        'salary_min': 0.25,
        'salary_max': 0.25,
    }

    # Merge: default_overrides là nền, field_error_thresholds ghi đè (ưu tiên cao hơn)
    resolved_overrides = {**default_overrides, **field_error_thresholds}

    if df.empty:
        return {}

    total_rows = len(df)

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

        # Sử dụng resolved_overrides thay vì field_error_thresholds gốc
        current_error = resolved_overrides.get(field, error_threshold)

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