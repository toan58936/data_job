"""
test_experience.py - Unit test cho processor experience
"""
import pytest
from transform.src.processors.experience import parse_experience


# ==================== TEST VỚI PARAMETRIZE ====================
@pytest.mark.parametrize("input_val, expected", [
    ("3 năm", (3, 3)),
    ("1 năm", (1, 1)),
    ("Trên 5 năm", (5, None)),
    ("Dưới 1 năm", (0, 1)),
    ("Không yêu cầu", (0, None)),
    ("2-3 năm", (2, 3)),
    ("5+ năm", (5, None)),
    ("5 năm kinh nghiệm", (5, 5)),
    ("2-3", (2, 3)),
    ("Fresher", (0, 0)),
    ("Intern", (0, 0)),
    ("", (None, None)),
    (None, (None, None)),
    ("2.  liên quan (Relevant Experience)", (None, None)),
])
def test_parse_experience_parametrize(input_val, expected):
    """Kiểm tra parse_experience với các ca khác nhau."""
    assert parse_experience(input_val) == expected


# ==================== TEST VỚI DỮ LIỆU MẪU ====================
def test_parse_experience_with_sample(sample_jobs_all, sample_jobs_detail):
    """
    Kiểm tra parse_experience trên dữ liệu thật từ sample.
    """
    # Kiểm tra từ jobs_all
    for job in sample_jobs_all:
        raw = job.get("experience")
        exp_min, exp_max = parse_experience(raw)
        if raw and raw.strip() and raw not in ["", None]:
            # Nếu raw không rỗng thì exp_min phải khác None hoặc exp_max khác None
            assert (exp_min is not None) or (exp_max is not None), f"Failed for raw: {raw}"

    # Kiểm tra từ jobs_detail
    for job in sample_jobs_detail:
        raw = job.get("experience")
        exp_min, exp_max = parse_experience(raw)
        if raw and raw.strip() and raw not in ["", None]:
            assert (exp_min is not None) or (exp_max is not None), f"Failed for raw: {raw}"

        # Nếu experience không có, thì exp_min/exp_max phải là None
        if not raw or not raw.strip():
            assert exp_min is None and exp_max is None