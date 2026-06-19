# transform/tests/unit/test_domain.py
import pytest
from transform.src.processors.domain import extract_domain_keywords
from transform.src.utils.config import DOMAIN_KEYWORDS


@pytest.mark.parametrize("title, description, requirements, expected", [
    (
        "Data Engineer",
        "Build data warehouse and data lakehouse on AWS",
        "Experience with real-time streaming and data governance",
        ["data governance", "data lakehouse", "data warehouse", "real-time"]
    ),
    (
        "ML Engineer",
        "Build AI models for fintech",
        "Need experience with data mesh and data fabric",
        ["ai", "data fabric", "data mesh", "fintech"]
    ),
    (
        "Data Analyst",
        "No domain keyword here",
        "",
        []
    ),
])
def test_extract_domain_keywords(title, description, requirements, expected):
    result = extract_domain_keywords(title, description, requirements, DOMAIN_KEYWORDS)
    assert result == expected