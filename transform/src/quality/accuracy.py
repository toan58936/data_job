"""
accuracy.py - Giai đoạn 3: Kiểm tra tính chính xác (Accuracy)
============================================================

Phát hiện lỗi logic và outlier:
- is_negotiable = True nhưng salary_min/salary_max không null
- is_negotiable = False nhưng cả salary_min và salary_max đều null
- Lương VND > 500 triệu (outlier)
- Lương USD > 20000 (outlier)
- Kinh nghiệm > 15 năm (outlier)
"""

import pandas as pd
from typing import Dict, Any


def check_accuracy(
    df: pd.DataFrame,
    outlier_vnd_threshold: float = 500.0,
    outlier_usd_threshold: float = 20000.0,
    outlier_exp_threshold: int = 15
) -> Dict[str, Dict[str, Any]]:
    """
    Kiểm tra tính chính xác của dữ liệu.

    Args:
        df: DataFrame chứa dữ liệu Silver.
        outlier_vnd_threshold: Ngưỡng outlier cho VND (triệu).
        outlier_usd_threshold: Ngưỡng outlier cho USD.
        outlier_exp_threshold: Ngưỡng outlier cho kinh nghiệm (năm).

    Returns:
        Dict với cấu trúc:
        {
            'check_name': {
                'violations': int,
                'status': str,  # 'OK', 'WARNING' (không có ERROR)
                'details': List[Dict]
            },
            ...
        }
    """
    if df.empty:
        return {}

    results = {}

    # 3.1: is_negotiable = True nhưng salary_min hoặc salary_max có giá trị
    violations = []
    if 'is_negotiable' in df.columns and 'salary_min' in df.columns and 'salary_max' in df.columns:
        mask = (df['is_negotiable'] == True) & (
            df['salary_min'].notna() | df['salary_max'].notna()
        )
        if mask.any():
            violations = df[mask][['job_url', 'is_negotiable', 'salary_min', 'salary_max']].to_dict('records')
    results['accurate_negotiable_salary'] = {
        'violations': len(violations),
        'status': 'OK' if len(violations) == 0 else 'WARNING',
        'details': violations
    }

    # 3.2: is_negotiable = False nhưng cả salary_min và salary_max đều null
    violations = []
    if 'is_negotiable' in df.columns and 'salary_min' in df.columns and 'salary_max' in df.columns:
        mask = (df['is_negotiable'] == False) & df['salary_min'].isna() & df['salary_max'].isna()
        if mask.any():
            violations = df[mask][['job_url', 'is_negotiable', 'salary_min', 'salary_max']].to_dict('records')
    results['accurate_non_negotiable_salary'] = {
        'violations': len(violations),
        'status': 'OK' if len(violations) == 0 else 'WARNING',
        'details': violations
    }

    # 3.3: Outlier VND (>500 triệu)
    violations = []
    if 'salary_min' in df.columns and 'salary_max' in df.columns and 'currency' in df.columns:
        # Lọc các job có currency = 'VND'
        vnd_mask = df['currency'] == 'VND'
        if vnd_mask.any():
            # Lọc job có ít nhất một trong salary_min/salary_max vượt ngưỡng
            outlier_mask = vnd_mask & (
                (df['salary_min'].notna() & (df['salary_min'] > outlier_vnd_threshold)) |
                (df['salary_max'].notna() & (df['salary_max'] > outlier_vnd_threshold))
            )
            if outlier_mask.any():
                violations = df[outlier_mask][['job_url', 'currency', 'salary_min', 'salary_max']].to_dict('records')
    results['outlier_salary_vnd'] = {
        'violations': len(violations),
        'status': 'WARNING' if len(violations) > 0 else 'OK',
        'details': violations
    }

    # 3.4: Outlier USD (>20000)
    violations = []
    if 'salary_min' in df.columns and 'salary_max' in df.columns and 'currency' in df.columns:
        usd_mask = df['currency'] == 'USD'
        if usd_mask.any():
            outlier_mask = usd_mask & (
                (df['salary_min'].notna() & (df['salary_min'] > outlier_usd_threshold)) |
                (df['salary_max'].notna() & (df['salary_max'] > outlier_usd_threshold))
            )
            if outlier_mask.any():
                violations = df[outlier_mask][['job_url', 'currency', 'salary_min', 'salary_max']].to_dict('records')
    results['outlier_salary_usd'] = {
        'violations': len(violations),
        'status': 'WARNING' if len(violations) > 0 else 'OK',
        'details': violations
    }

    # 3.5: Outlier kinh nghiệm (>15 năm)
    violations = []
    if 'exp_min' in df.columns and 'exp_max' in df.columns:
        outlier_mask = (
            (df['exp_min'].notna() & (df['exp_min'] > outlier_exp_threshold)) |
            (df['exp_max'].notna() & (df['exp_max'] > outlier_exp_threshold))
        )
        if outlier_mask.any():
            violations = df[outlier_mask][['job_url', 'exp_min', 'exp_max']].to_dict('records')
    results['outlier_exp'] = {
        'violations': len(violations),
        'status': 'WARNING' if len(violations) > 0 else 'OK',
        'details': violations
    }

    return results