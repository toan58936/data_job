"""
validity.py - Giai đoạn 2: Kiểm tra tính hợp lệ (Validity)
===========================================================

Kiểm tra các ràng buộc logic trên dữ liệu:
- salary_min <= salary_max
- exp_min <= exp_max
- currency ∈ {VND, USD, null}
- work_mode ∈ {Onsite, Hybrid, Remote, null}
- seniority_level ∈ {Junior, Middle, Senior, Lead, Unknown, null}
- deadline đúng định dạng YYYY-MM-DD
"""

import pandas as pd
from typing import Dict, Any, List


def check_validity(
    df: pd.DataFrame,
    warning_threshold: int = 5,
    error_threshold: int = 15
) -> Dict[str, Dict[str, Any]]:
    """
    Kiểm tra tính hợp lệ của các trường.

    Args:
        df: DataFrame chứa dữ liệu Silver.
        warning_threshold: Số lượng vi phạm để cảnh báo (mặc định 5).
        error_threshold: Số lượng vi phạm để báo lỗi (mặc định 15).

    Returns:
        Dict với cấu trúc:
        {
            'check_name': {
                'violations': int,          # Số job vi phạm
                'status': str,              # 'OK', 'WARNING', 'ERROR'
                'details': List[Dict]       # Chi tiết job vi phạm (URL, giá trị...)
            },
            ...
        }
    """
    if df.empty:
        return {}

    results = {}

    # 2.1: salary_min > salary_max
    violations = []
    if 'salary_min' in df.columns and 'salary_max' in df.columns:
        mask = df['salary_min'].notna() & df['salary_max'].notna() & (df['salary_min'] > df['salary_max'])
        violations = df[mask][['job_url', 'salary_min', 'salary_max']].to_dict('records')
    results['valid_salary_range'] = {
        'violations': len(violations),
        'status': _determine_status(len(violations), warning_threshold, error_threshold),
        'details': violations
    }

    # 2.2: exp_min > exp_max
    violations = []
    if 'exp_min' in df.columns and 'exp_max' in df.columns:
        mask = df['exp_min'].notna() & df['exp_max'].notna() & (df['exp_min'] > df['exp_max'])
        violations = df[mask][['job_url', 'exp_min', 'exp_max']].to_dict('records')
    results['valid_exp_range'] = {
        'violations': len(violations),
        'status': _determine_status(len(violations), warning_threshold, error_threshold),
        'details': violations
    }

    # 2.3: valid_currency - phải thuộc {VND, USD, null}
    violations = []
    if 'currency' in df.columns:
        valid_values = ['VND', 'USD', None]
        # Nếu giá trị không nằm trong valid_values
        mask = ~df['currency'].isin(valid_values) & df['currency'].notna()
        violations = df[mask][['job_url', 'currency']].to_dict('records')
    results['valid_currency'] = {
        'violations': len(violations),
        'status': _determine_status(len(violations), warning_threshold, error_threshold),
        'details': violations
    }

    # 2.4: valid_work_mode - phải thuộc {Onsite, Hybrid, Remote, null}
    violations = []
    if 'work_mode' in df.columns:
        valid_values = ['Onsite', 'Hybrid', 'Remote', None]
        mask = ~df['work_mode'].isin(valid_values) & df['work_mode'].notna()
        violations = df[mask][['job_url', 'work_mode']].to_dict('records')
    results['valid_work_mode'] = {
        'violations': len(violations),
        'status': _determine_status(len(violations), warning_threshold, error_threshold),
        'details': violations
    }

    # 2.5: valid_seniority_level - phải thuộc {Junior, Middle, Senior, Lead, Unknown, null}
    violations = []
    if 'seniority_level' in df.columns:
        valid_values = ['Junior', 'Middle', 'Senior', 'Lead', 'Unknown', None]
        mask = ~df['seniority_level'].isin(valid_values) & df['seniority_level'].notna()
        violations = df[mask][['job_url', 'seniority_level']].to_dict('records')
    results['valid_seniority_level'] = {
        'violations': len(violations),
        'status': _determine_status(len(violations), warning_threshold, error_threshold),
        'details': violations
    }

    # 2.6: valid_deadline_format - phải đúng định dạng YYYY-MM-DD
    violations = []
    if 'deadline' in df.columns:
        # Kiểm tra định dạng chuỗi (loại bỏ NaN)
        mask_deadline = df['deadline'].notna()
        if mask_deadline.any():
            # Thử parse datetime, nếu lỗi thì coi là vi phạm
            def is_valid_date(val):
                if pd.isna(val):
                    return True
                try:
                    pd.to_datetime(val, format='%Y-%m-%d')
                    return True
                except:
                    return False
            invalid = df[mask_deadline].apply(lambda row: not is_valid_date(row['deadline']), axis=1)
            violations = df[mask_deadline & invalid][['job_url', 'deadline']].to_dict('records')
    results['valid_deadline_format'] = {
        'violations': len(violations),
        'status': _determine_status(len(violations), warning_threshold, error_threshold),
        'details': violations
    }

    return results


def _determine_status(violations: int, warning_threshold: int, error_threshold: int) -> str:
    """Xác định trạng thái dựa trên số lượng vi phạm."""
    if violations <= warning_threshold:
        return 'OK'
    elif violations <= error_threshold:
        return 'WARNING'
    else:
        return 'ERROR'