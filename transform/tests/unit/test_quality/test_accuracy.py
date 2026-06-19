"""
Unit test cho accuracy.py
"""

import pandas as pd
from transform.src.quality.accuracy import check_accuracy


def test_accuracy_all_ok():
    """Trường hợp tất cả đều đúng."""
    df = pd.DataFrame({
        'job_url': ['url1', 'url2'],
        'is_negotiable': [False, False],
        'salary_min': [10.0, 20.0],
        'salary_max': [15.0, 25.0],
        'currency': ['VND', 'VND'],
        'exp_min': [2, 3],
        'exp_max': [4, 5]
    })
    result = check_accuracy(df)
    for check_name, data in result.items():
        assert data['violations'] == 0
        assert data['status'] == 'OK'


def test_accuracy_negotiable_salary_wrong():
    """is_negotiable=True nhưng salary_min/salary_max không null."""
    df = pd.DataFrame({
        'job_url': ['url1', 'url2'],
        'is_negotiable': [True, False],
        'salary_min': [10.0, None],
        'salary_max': [15.0, None]
    })
    result = check_accuracy(df)
    assert result['accurate_negotiable_salary']['violations'] == 1
    assert result['accurate_negotiable_salary']['status'] == 'WARNING'
    assert len(result['accurate_negotiable_salary']['details']) == 1
    assert result['accurate_negotiable_salary']['details'][0]['job_url'] == 'url1'


def test_accuracy_non_negotiable_salary_wrong():
    """is_negotiable=False nhưng cả salary_min và salary_max đều null."""
    df = pd.DataFrame({
        'job_url': ['url1', 'url2'],
        'is_negotiable': [False, True],
        'salary_min': [None, None],
        'salary_max': [None, None]
    })
    result = check_accuracy(df)
    assert result['accurate_non_negotiable_salary']['violations'] == 1
    assert result['accurate_non_negotiable_salary']['status'] == 'WARNING'
    assert len(result['accurate_non_negotiable_salary']['details']) == 1
    assert result['accurate_non_negotiable_salary']['details'][0]['job_url'] == 'url1'


def test_accuracy_outlier_vnd():
    """Outlier salary trong VND (>500 triệu)."""
    df = pd.DataFrame({
        'job_url': ['url1', 'url2', 'url3'],
        'currency': ['VND', 'VND', 'VND'],
        'salary_min': [600.0, 10.0, 700.0],
        'salary_max': [700.0, 15.0, 800.0]
    })
    result = check_accuracy(df)
    # url1 và url3 đều vi phạm (ít nhất một trường >500)
    assert result['outlier_salary_vnd']['violations'] == 2
    assert result['outlier_salary_vnd']['status'] == 'WARNING'
    assert len(result['outlier_salary_vnd']['details']) == 2


def test_accuracy_outlier_usd():
    """Outlier salary trong USD (>20000)."""
    df = pd.DataFrame({
        'job_url': ['url1', 'url2'],
        'currency': ['USD', 'USD'],
        'salary_min': [25000.0, 5000.0],
        'salary_max': [30000.0, 7000.0]
    })
    result = check_accuracy(df)
    # url1: cả min và max đều >20000 -> 1 vi phạm
    assert result['outlier_salary_usd']['violations'] == 1
    assert result['outlier_salary_usd']['status'] == 'WARNING'
    assert len(result['outlier_salary_usd']['details']) == 1
    assert result['outlier_salary_usd']['details'][0]['job_url'] == 'url1'


def test_accuracy_outlier_exp():
    """Outlier kinh nghiệm (>15 năm)."""
    df = pd.DataFrame({
        'job_url': ['url1', 'url2', 'url3'],
        'exp_min': [10, 20, 18],
        'exp_max': [12, 25, 19]
    })
    result = check_accuracy(df)
    # url2 và url3 vi phạm (exp_min=20>15, exp_max=25>15; url3 có exp_min=18>15)
    assert result['outlier_exp']['violations'] == 2
    assert result['outlier_exp']['status'] == 'WARNING'
    assert len(result['outlier_exp']['details']) == 2


def test_accuracy_empty_dataframe():
    """Trường hợp DataFrame rỗng."""
    df = pd.DataFrame()
    result = check_accuracy(df)
    assert result == {}


def test_accuracy_missing_columns():
    """Trường hợp thiếu một số cột."""
    df = pd.DataFrame({
        'job_url': ['url1'],
        'is_negotiable': [False]
    })
    result = check_accuracy(df)
    # Các kiểm tra bỏ qua cột thiếu sẽ có violations=0 và status='OK'
    assert result['accurate_negotiable_salary']['violations'] == 0
    assert result['accurate_negotiable_salary']['status'] == 'OK'
    assert result['outlier_exp']['violations'] == 0
    assert result['outlier_exp']['status'] == 'OK'