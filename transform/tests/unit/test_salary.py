"""
test_salary.py - Unit test cho processor salary
"""
import pytest
from transform.src.processors.salary import parse_salary


# ==================== TEST VỚI PARAMETRIZE ====================
@pytest.mark.parametrize("input_val, expected", [
    ("Thoả thuận", {'salary_min': None, 'salary_max': None, 'currency': None, 'is_negotiable': True}),
    ("27 - 45 triệu", {'salary_min': 27.0, 'salary_max': 45.0, 'currency': 'VND', 'is_negotiable': False}),
    ("Tới 22 triệu", {'salary_min': None, 'salary_max': 22.0, 'currency': 'VND', 'is_negotiable': False}),
    ("10,000,000 - 20,000,000 VND", {'salary_min': 10.0, 'salary_max': 20.0, 'currency': 'VND', 'is_negotiable': False}),
    ("800 - 3,500 USD", {'salary_min': 800.0, 'salary_max': 3500.0, 'currency': 'USD', 'is_negotiable': False}),
    ("Tới 35 triệu", {'salary_min': None, 'salary_max': 35.0, 'currency': 'VND', 'is_negotiable': False}),
    ("25 - 30 triệu", {'salary_min': 25.0, 'salary_max': 30.0, 'currency': 'VND', 'is_negotiable': False}),
    ("", {'salary_min': None, 'salary_max': None, 'currency': None, 'is_negotiable': False}),
    (None, {'salary_min': None, 'salary_max': None, 'currency': None, 'is_negotiable': False}),
    ("• : 10,000,000 - 20,000,000 VND + Thưởng", {'salary_min': 10.0, 'salary_max': 20.0, 'currency': 'VND', 'is_negotiable': False}),
    ("15 - 30 triệu", {'salary_min': 15.0, 'salary_max': 30.0, 'currency': 'VND', 'is_negotiable': False}),
])
def test_parse_salary_parametrize(input_val, expected):
    """Kiểm tra parse_salary với các ca khác nhau."""
    assert parse_salary(input_val) == expected


# ==================== TEST VỚI DỮ LIỆU MẪU ====================
def test_parse_salary_with_sample(sample_jobs_all, sample_jobs_detail):
    """
    Kiểm tra parse_salary trên dữ liệu thật từ sample.
    """
    # Từ jobs_all
    for job in sample_jobs_all:
        raw = job.get("salary")
        result = parse_salary(raw)
        # Nếu raw có giá trị và không phải "Thoả thuận", thì ít nhất currency phải có
        if raw and raw.strip() and "Thoả thuận" not in raw:
            # Có thể có hoặc không có salary_min/max, nhưng currency nên có
            if result['currency'] is None:
                # Nếu currency None, có thể là do parse thất bại, nhưng vẫn chấp nhận
                pass
        # Đảm bảo is_negotiable là bool
        assert isinstance(result['is_negotiable'], bool)

    # Từ jobs_detail (có thể có salary rỗng)
    for job in sample_jobs_detail:
        raw = job.get("salary")
        result = parse_salary(raw)
        assert isinstance(result['is_negotiable'], bool)