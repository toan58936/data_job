"""
test_role.py - Unit test cho processor role
"""
import pytest
from transform.src.processors.role import normalize_role


@pytest.mark.parametrize("title, expected", [
    ("Senior Data Engineer", "Data Engineer"),
    ("Data Analyst", "Data Analyst"),
    ("Data Scientist", "Data Scientist"),
    ("BI Analyst", "BI Analyst"),
    ("Business Intelligence", "BI Analyst"),
    ("Machine Learning Engineer", "ML Engineer"),
    ("ML Engineer", "ML Engineer"),
    ("AI Engineer", "AI Engineer"),
    ("Database Engineer", "Database Engineer"),
    ("Database Administrator", "Database Engineer"),
    ("DBA", "Database Engineer"),
    ("Data Architect", "Data Architect"),
    ("Data Platform Engineer", "Data Platform Engineer"),
    ("ETL Developer", "ETL Developer"),
    ("DataOps Engineer", "DataOps Engineer"),
    ("Analytics Engineer", "Analytics Engineer"),
    ("Unknown Title", "Data Engineer"),  # default
    ("", None),
    (None, None),
])
def test_normalize_role(title, expected):
    assert normalize_role(title) == expected