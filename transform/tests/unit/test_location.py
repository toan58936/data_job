"""
test_location.py - Unit test cho processor location
"""
import re
import pytest
from transform.src.processors.location import clean_location


# ==================== TEST VỚI DỮ LIỆU MẪU ====================
def test_clean_location_with_sample(sample_jobs_all):
    """
    Kiểm tra clean_location trên dữ liệu thật từ sample.
    """
    for job in sample_jobs_all:
        raw = job.get("location")
        cleaned = clean_location(raw)
        # In ra để debug nếu cần, nhưng pytest sẽ capture output
        # Chỉ kiểm tra nếu raw không rỗng thì cleaned phải khác None hoặc khác rỗng
        if raw and raw.strip():
            assert cleaned is not None
            assert isinstance(cleaned, str)
            assert len(cleaned) > 0


# ==================== TEST VỚI PARAMETRIZE ====================
@pytest.mark.parametrize("input_val, expected", [
    # Trường hợp thông thường
    ("Hà Nội", "Hà Nội"),
    ("Hồ Chí Minh", "Hồ Chí Minh"),
    ("Đà Nẵng", "Đà Nẵng"),
    
    # Trường hợp có hậu tố (mới), (cũ)
    ("Hồ Chí Minh (mới)", "Hồ Chí Minh"),
    ("Đà Nẵng (mới)", "Đà Nẵng"),
    ("Hưng Yên (mới)", "Hưng Yên"),
    
    # Trường hợp có tiền tố "Việc làm tại"
    ("Việc làm tại Hà Nội", "Hà Nội"),
    ("Việc làm tại Hồ Chí Minh", "Hồ Chí Minh"),
    
    # Trường hợp nhiều địa điểm
    ("Hà Nội & Hồ Chí Minh", "Hà Nội"),
    ("Hà Nội, Hồ Chí Minh", "Hà Nội"),
    ("Hà Nội - Hồ Chí Minh", "Hà Nội"),
    
    # Trường hợp rỗng
    ("", None),
    (None, None),
    
    # Trường hợp không có trong mapping
    ("Tokyo", "Tokyo"),  # giữ nguyên
])
def test_clean_location_parametrize(input_val, expected):
    """Kiểm tra clean_location với các ca khác nhau."""
    assert clean_location(input_val) == expected


# ==================== TEST VỚI DỮ LIỆU TỪ DETAIL ====================
def test_clean_location_from_detail(sample_jobs_detail):
    """
    Kiểm tra clean_location trên dữ liệu detail (có cả location_detail).
    """
    for job in sample_jobs_detail:
        raw = job.get("location")
        cleaned = clean_location(raw)
        location_detail = job.get("location_detail")
        # Nếu có location_detail, kiểm tra cleaned có nằm trong danh sách thành phố xuất hiện trong location_detail hay không
        if location_detail:
            # Tìm tất cả thành phố có trong mapping
            from transform.src.utils.config import LOCATION_MAPPING
            cities = list(LOCATION_MAPPING.keys())
            # Tìm các thành phố xuất hiện trong location_detail
            found_cities = [city for city in cities if city in location_detail]
            if found_cities:
                # cleaned phải là một trong các thành phố đó (hoặc là None nếu raw rỗng, nhưng nếu raw có thì cleaned không None)
                if raw and raw.strip():
                    assert cleaned in found_cities
                else:
                    # Nếu raw rỗng, clean_location sẽ trả về None, không cần kiểm tra
                    assert cleaned is None
            else:
                # Nếu không có thành phố nào trong location_detail, không kiểm tra
                pass