"""
timeliness.py - Giai đoạn 5: Kiểm tra tính kịp thời (Timeliness)
================================================================

Kiểm tra xem dữ liệu có bị "cũ" không (crawled_at > threshold days ago).
"""

import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, Any


def check_timeliness(
    df: pd.DataFrame,
    days_threshold: int = 30,
    warning_percentage: float = 0.20
) -> Dict[str, Any]:
    """
    Kiểm tra tính kịp thời của dữ liệu.

    Args:
        df: DataFrame chứa dữ liệu Silver.
        days_threshold: Số ngày tối đa cho phép (mặc định 30).
        warning_percentage: Tỷ lệ job cũ để cảnh báo (mặc định 20%).

    Returns:
        Dict với cấu trúc:
        {
            'stale_data': {
                'stale_count': int,          # Số job cũ
                'total': int,                # Tổng số job
                'percentage': float,         # Tỷ lệ %
                'status': str                # 'OK' hoặc 'WARNING'
            }
        }
    """
    if df.empty:
        return {}

    if 'crawled_at' not in df.columns:
        return {
            'stale_data': {
                'stale_count': 0,
                'total': len(df),
                'percentage': 0.0,
                'status': 'OK',
                'error': 'Missing crawled_at column'
            }
        }

    # Tạo bản sao của cột crawled_at để xử lý (không ảnh hưởng df gốc)
    crawled = df['crawled_at'].copy()

    # Chuyển đổi sang datetime nếu cần
    if not pd.api.types.is_datetime64_any_dtype(crawled):
        crawled = pd.to_datetime(crawled)

    # Xử lý timezone: chuyển về naive (bỏ timezone) để so sánh
    if crawled.dt.tz is not None:
        crawled = crawled.dt.tz_convert(None)

    # Lấy thời gian hiện tại ở UTC và chuyển về naive để so sánh
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    threshold_date = now_utc - timedelta(days=days_threshold)

    # Đếm số job cũ (crawled_at < threshold_date)
    stale_mask = crawled < threshold_date
    stale_count = stale_mask.sum()
    total = len(df)
    percentage = (stale_count / total) * 100 if total > 0 else 0.0

    status = 'WARNING' if percentage > warning_percentage * 100 else 'OK'

    return {
        'stale_data': {
            'stale_count': int(stale_count),
            'total': total,
            'percentage': round(percentage, 2),
            'status': status
        }
    }