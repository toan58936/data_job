"""
test_seniority.py - Unit test cho processor seniority
"""
import pytest
from transform.src.processors.seniority import derive_seniority


@pytest.mark.parametrize("title, exp_min, expected", [
    ("Senior Data Engineer", 5, "Senior"),
    ("Junior Developer", 1, "Junior"),
    ("Data Engineer", 3, "Middle"),
    ("Lead Engineer", 7, "Lead"),
    ("Data Engineer", 0, "Junior"),
    ("Data Engineer", 2, "Middle"),
    ("Data Engineer", 5, "Senior"),
    ("Data Engineer", 8, "Lead"),
    ("Principal Engineer", 10, "Principal"),
    ("Staff Engineer", 6, "Staff"),
    ("Intern", 0, "Intern"),
    ("Fresher", 0, "Fresher"),
    ("", None, None),
    (None, None, None),
    ("Data Engineer", None, "Unknown"),  # exp_min None, no keyword -> Unknown
])
def test_derive_seniority(title, exp_min, expected):
    assert derive_seniority(title, exp_min) == expected