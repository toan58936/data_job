"""
Unit test cho validity.py
"""

import pandas as pd
import pytest
from transform.src.quality.validity import check_validity


def test_validity_all_ok():
    """Trường hợp tất cả các kiểm tra đều hợp lệ."""
    df = pd.DataFrame({
        'job_url': ['url1', 'url2'],
        'salary_min': [10, 20],
        'salary_max': [15, 25],
        'exp_min': [1, 2],
        'exp_max': [3, 4],
        'currency': ['VND', 'USD'],
        'work_mode': ['Onsite', 'Hybrid'],
        'seniority_level': ['Senior', 'Junior'],
        'deadline': ['2026-12-31', '2026-12-31']
    })
    result = check_validity(df)
    for check_name, data in result.items():
        assert data['status'] == 'OK'
        assert data['violations'] == 0


def test_validity_salary_range():
    """Kiểm tra salary_min > salary_max."""
    df = pd.DataFrame({
        'job_url': ['url1', 'url2', 'url3'],
        'salary_min': [10, 20, 30],
        'salary_max': [15, 18, 25]  # url2: 20 > 18 (violation), url3: 30 > 25 (violation)
    })
    result = check_validity(df)
    assert result['valid_salary_range']['violations'] == 2
    # Sửa: 2 <= 5 -> OK
    assert result['valid_salary_range']['status'] == 'OK'   # <-- THAY ĐỔI

def test_validity_exp_range():
    """Kiểm tra exp_min > exp_max."""
    df = pd.DataFrame({
        'job_url': ['url1', 'url2'],
        'exp_min': [5, 2],
        'exp_max': [3, 4]   # url1: 5 > 3 (violation)
    })
    result = check_validity(df)
    assert result['valid_exp_range']['violations'] == 1
    # details chứa job vi phạm
    assert len(result['valid_exp_range']['details']) == 1
    assert result['valid_exp_range']['details'][0]['job_url'] == 'url1'


def test_validity_currency():
    """Kiểm tra currency không nằm trong {VND, USD, null}."""
    df = pd.DataFrame({
        'job_url': ['url1', 'url2', 'url3'],
        'currency': ['VND', 'EUR', None]  # EUR là vi phạm
    })
    result = check_validity(df)
    assert result['valid_currency']['violations'] == 1
    assert result['valid_currency']['details'][0]['currency'] == 'EUR'


def test_validity_work_mode():
    """Kiểm tra work_mode không nằm trong {Onsite, Hybrid, Remote, null}."""
    df = pd.DataFrame({
        'job_url': ['url1', 'url2'],
        'work_mode': ['Onsite', 'Flexible']  # Flexible là vi phạm
    })
    result = check_validity(df)
    assert result['valid_work_mode']['violations'] == 1
    assert result['valid_work_mode']['details'][0]['work_mode'] == 'Flexible'


def test_validity_seniority_level():
    """Kiểm tra seniority_level không nằm trong danh sách cho phép."""
    df = pd.DataFrame({
        'job_url': ['url1'],
        'seniority_level': ['Expert']  # Expert không hợp lệ
    })
    result = check_validity(df)
    assert result['valid_seniority_level']['violations'] == 1
    assert result['valid_seniority_level']['details'][0]['seniority_level'] == 'Expert'


def test_validity_deadline_format():
    """Kiểm tra định dạng deadline."""
    df = pd.DataFrame({
        'job_url': ['url1', 'url2', 'url3'],
        'deadline': ['2026-12-31', '31/12/2026', None]  # 31/12/2026 là vi phạm
    })
    result = check_validity(df)
    assert result['valid_deadline_format']['violations'] == 1
    assert result['valid_deadline_format']['details'][0]['deadline'] == '31/12/2026'


def test_validity_empty_dataframe():
    """Trường hợp DataFrame rỗng."""
    df = pd.DataFrame()
    result = check_validity(df)
    assert result == {}


def test_validity_missing_columns():
    """Trường hợp thiếu một số cột."""
    df = pd.DataFrame({
        'job_url': ['url1'],
        'salary_min': [10],
        # thiếu salary_max, exp_min, exp_max, ...
    })
    result = check_validity(df)
    # Các kiểm tra với cột thiếu sẽ có violations=0 và status='OK'
    assert result['valid_salary_range']['violations'] == 0
    assert result['valid_salary_range']['status'] == 'OK'
    assert result['valid_exp_range']['violations'] == 0
    assert result['valid_exp_range']['status'] == 'OK'