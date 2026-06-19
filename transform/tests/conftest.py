"""
conftest.py - Fixtures dùng chung cho tất cả test
"""
import json
import pytest
from pathlib import Path


@pytest.fixture
def sample_jobs_all():
    """Load dữ liệu mẫu từ sample_jobs_all.json"""
    path = Path(__file__).parent / "fixtures" / "sample_jobs_all.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_jobs_detail():
    """Load dữ liệu mẫu từ sample_jobs_detail.json"""
    path = Path(__file__).parent / "fixtures" / "sample_jobs_detail.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_jobs_text():
    """Load dữ liệu mẫu từ sample_jobs_text.json"""
    path = Path(__file__).parent / "fixtures" / "sample_jobs_text.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)