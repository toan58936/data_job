"""
uniqueness.py - Giai đoạn 4: Kiểm tra trùng lặp và nhất quán
=============================================================

Kiểm tra:
- duplicate_job_url: Số lượng job_url trùng lặp.
- role_title_consistency: Số job có normalized_role không khớp với từ khóa trong title.
"""

import pandas as pd
import re
from typing import Dict, Any, List


# Mapping role -> từ khóa cần có trong title (tối thiểu một từ)
ROLE_KEYWORDS = {
    'Data Engineer': ['data', 'engineer'],
    'Data Analyst': ['data', 'analyst'],
    'Data Scientist': ['data', 'scientist'],
    'BI Analyst': ['bi', 'business intelligence', 'analyst'],
    'ML Engineer': ['machine learning', 'ml', 'engineer'],
    'AI Engineer': ['ai', 'artificial intelligence', 'engineer'],
    'Database Engineer': ['database', 'db', 'engineer'],
    'Data Architect': ['data', 'architect'],
    'Data Platform Engineer': ['data', 'platform', 'engineer'],
    'ETL Developer': ['etl', 'developer'],
    'DataOps Engineer': ['dataops', 'data ops', 'engineer'],
    'Analytics Engineer': ['analytics', 'engineer'],
}


def check_uniqueness(
    df: pd.DataFrame,
    warning_duplicate_threshold: int = 2,
    warning_consistency_threshold: int = 5
) -> Dict[str, Dict[str, Any]]:
    """
    Kiểm tra trùng lặp và nhất quán.

    Args:
        df: DataFrame chứa dữ liệu Silver.
        warning_duplicate_threshold: Số URL trùng để cảnh báo (mặc định 2).
        warning_consistency_threshold: Số job không nhất quán để cảnh báo (mặc định 5).

    Returns:
        Dict với cấu trúc:
        {
            'duplicate_job_url': {
                'violations': int,
                'status': str,          # 'OK' hoặc 'WARNING'
                'details': List[Dict]   # URL và số lần xuất hiện
            },
            'role_title_consistency': {
                'violations': int,
                'status': str,
                'details': List[Dict]   # job_url, title, normalized_role
            }
        }
    """
    if df.empty:
        return {}

    results = {}

    # 4.1: duplicate_job_url
    violations = []
    if 'job_url' in df.columns:
        url_counts = df['job_url'].value_counts()
        duplicated_urls = url_counts[url_counts > 1]
        violations = [
            {'job_url': url, 'count': int(count)}
            for url, count in duplicated_urls.items()
        ]
    results['duplicate_job_url'] = {
        'violations': len(violations),
        'status': 'WARNING' if len(violations) > warning_duplicate_threshold else 'OK',
        'details': violations
    }

    # 4.2: role_title_consistency
    violations = []
    if 'job_url' in df.columns and 'title' in df.columns and 'normalized_role' in df.columns:
        for idx, row in df.iterrows():
            role = row.get('normalized_role')
            title = row.get('title')
            if pd.isna(role) or pd.isna(title):
                continue
            role = str(role)
            title = str(title).lower()
            # Lấy danh sách từ khóa cho role đó
            keywords = ROLE_KEYWORDS.get(role, [])
            if not keywords:
                # Nếu role không có trong mapping, coi là không khớp
                violations.append({
                    'job_url': row['job_url'],
                    'title': title,
                    'normalized_role': role,
                    'reason': 'unknown_role'
                })
                continue
            # Kiểm tra ít nhất một từ khóa có trong title
            matched = any(kw in title for kw in keywords)
            if not matched:
                violations.append({
                    'job_url': row['job_url'],
                    'title': title,
                    'normalized_role': role,
                    'reason': 'no_keyword_match'
                })
    results['role_title_consistency'] = {
        'violations': len(violations),
        'status': 'WARNING' if len(violations) > warning_consistency_threshold else 'OK',
        'details': violations
    }

    return results