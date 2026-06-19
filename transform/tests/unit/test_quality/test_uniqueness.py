"""
Unit test cho uniqueness.py
"""

import pandas as pd
from transform.src.quality.uniqueness import check_uniqueness


def test_uniqueness_all_ok():
    """Trường hợp không có trùng lặp và tất cả role đều nhất quán."""
    df = pd.DataFrame({
        'job_url': ['url1', 'url2', 'url3'],
        'title': ['Data Engineer', 'Data Analyst', 'ML Engineer'],
        'normalized_role': ['Data Engineer', 'Data Analyst', 'ML Engineer']
    })
    result = check_uniqueness(df)
    assert result['duplicate_job_url']['violations'] == 0
    assert result['duplicate_job_url']['status'] == 'OK'
    assert result['role_title_consistency']['violations'] == 0
    assert result['role_title_consistency']['status'] == 'OK'


def test_uniqueness_duplicate_url():
    """Trường hợp có URL trùng lặp."""
    df = pd.DataFrame({
        'job_url': ['url1', 'url1', 'url2'],
        'title': ['DE', 'DE', 'DA'],
        'normalized_role': ['Data Engineer', 'Data Engineer', 'Data Analyst']
    })
    result = check_uniqueness(df)
    assert result['duplicate_job_url']['violations'] == 1
    assert result['duplicate_job_url']['details'][0]['job_url'] == 'url1'
    assert result['duplicate_job_url']['details'][0]['count'] == 2
    # 1 violation <= 2 -> OK
    assert result['duplicate_job_url']['status'] == 'OK'


def test_uniqueness_duplicate_url_warning():
    """Trường hợp có nhiều URL trùng lặp (>2)."""
    df = pd.DataFrame({
        'job_url': ['url1', 'url1', 'url1', 'url2', 'url2', 'url3'],
        'title': ['DE']*6,
        'normalized_role': ['Data Engineer']*6
    })
    result = check_uniqueness(df)
    # url1: 3 lần, url2: 2 lần -> 2 violations
    assert result['duplicate_job_url']['violations'] == 2
    # 2 > 2? Không, bằng -> OK (vì threshold là >2)
    # Để test WARNING, cần 3 violations
    df2 = pd.DataFrame({
        'job_url': ['url1', 'url1', 'url1', 'url2', 'url2', 'url2', 'url3', 'url3', 'url3'],
        'title': ['DE']*9,
        'normalized_role': ['Data Engineer']*9
    })
    result2 = check_uniqueness(df2)
    # 3 violations (url1, url2, url3) -> >2 -> WARNING
    assert result2['duplicate_job_url']['violations'] == 3
    assert result2['duplicate_job_url']['status'] == 'WARNING'


def test_uniqueness_role_consistency():
    """Kiểm tra role-title consistency."""
    df = pd.DataFrame({
        'job_url': ['url1', 'url2', 'url3'],
        'title': ['Data Engineer', 'Data Analyst', 'Software Developer'],  # <-- sửa từ 'Software Engineer' thành 'Software Developer'
        'normalized_role': ['Data Engineer', 'Data Analyst', 'Data Engineer']
    })
    result = check_uniqueness(df)
    # url3: role là Data Engineer nhưng title không có 'data' hoặc 'engineer' -> vi phạm
    assert result['role_title_consistency']['violations'] == 1
    assert result['role_title_consistency']['details'][0]['job_url'] == 'url3'
    # 1 <= 5 -> OK
    assert result['role_title_consistency']['status'] == 'OK'


def test_uniqueness_role_consistency_warning():
    """Trường hợp có nhiều vi phạm consistency (>5)."""
    data = []
    for i in range(7):
        data.append({
            'job_url': f'url{i}',
            'title': f'Some Random Title {i}',
            'normalized_role': 'Data Engineer'
        })
    df = pd.DataFrame(data)
    result = check_uniqueness(df)
    # Tất cả 7 đều vi phạm (vì title không chứa 'data' hoặc 'engineer')
    assert result['role_title_consistency']['violations'] == 7
    assert result['role_title_consistency']['status'] == 'WARNING'


def test_uniqueness_missing_columns():
    """Trường hợp thiếu cột."""
    df = pd.DataFrame({
        'job_url': ['url1'],
        'title': ['DE']
        # thiếu normalized_role
    })
    result = check_uniqueness(df)
    # duplicate check vẫn chạy được
    assert 'duplicate_job_url' in result
    # role_title_consistency không có dữ liệu -> violations=0
    assert result['role_title_consistency']['violations'] == 0
    assert result['role_title_consistency']['status'] == 'OK'


def test_uniqueness_empty_dataframe():
    """Trường hợp DataFrame rỗng."""
    df = pd.DataFrame()
    result = check_uniqueness(df)
    assert result == {}