"""
Unit test cho timeliness.py
"""

import pandas as pd
from datetime import datetime, timedelta
from transform.src.quality.timeliness import check_timeliness


def test_timeliness_all_fresh():
    """Trường hợp tất cả dữ liệu đều mới (trong vòng 30 ngày)."""
    now = datetime.now()
    df = pd.DataFrame({
        'crawled_at': [
            now - timedelta(days=5),
            now - timedelta(days=10),
            now - timedelta(days=20)
        ]
    })
    result = check_timeliness(df)
    assert result['stale_data']['stale_count'] == 0
    assert result['stale_data']['percentage'] == 0.0
    assert result['stale_data']['status'] == 'OK'


def test_timeliness_some_stale():
    """Trường hợp có một số job cũ nhưng dưới ngưỡng 20%."""
    now = datetime.now()
    df = pd.DataFrame({
        'crawled_at': [
            now - timedelta(days=5),
            now - timedelta(days=10),
            now - timedelta(days=35),  # stale
            now - timedelta(days=40),  # stale
        ]
    })
    result = check_timeliness(df)
    # 2/4 = 50% > 20% -> WARNING
    assert result['stale_data']['stale_count'] == 2
    assert result['stale_data']['percentage'] == 50.0
    assert result['stale_data']['status'] == 'WARNING'


def test_timeliness_below_warning_threshold():
    """Trường hợp có job cũ nhưng dưới ngưỡng cảnh báo 20%."""
    now = datetime.now()
    df = pd.DataFrame({
        'crawled_at': [
            now - timedelta(days=5),
            now - timedelta(days=10),
            now - timedelta(days=35),  # 1/10 = 10% < 20%
            now - timedelta(days=5),
            now - timedelta(days=10),
            now - timedelta(days=5),
            now - timedelta(days=10),
            now - timedelta(days=5),
            now - timedelta(days=10),
            now - timedelta(days=5),
        ]
    })
    result = check_timeliness(df)
    assert result['stale_data']['stale_count'] == 1
    assert result['stale_data']['percentage'] == 10.0
    assert result['stale_data']['status'] == 'OK'


def test_timeliness_missing_column():
    """Trường hợp thiếu cột crawled_at."""
    df = pd.DataFrame({'title': ['Job1', 'Job2']})
    result = check_timeliness(df)
    assert result['stale_data']['stale_count'] == 0
    assert result['stale_data']['percentage'] == 0.0
    assert result['stale_data']['status'] == 'OK'
    assert 'error' in result['stale_data']


def test_timeliness_empty_dataframe():
    """Trường hợp DataFrame rỗng."""
    df = pd.DataFrame()
    result = check_timeliness(df)
    assert result == {}