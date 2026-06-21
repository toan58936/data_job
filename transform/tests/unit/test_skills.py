"""
test_skills.py - Unit test cho processor skills
"""
import pytest
from transform.src.processors.skills import extract_skills
from transform.src.utils.config import SKILL_KEYWORDS


# ==================== TEST VỚI PARAMETRIZE ====================
@pytest.mark.parametrize("title, description, requirements, expected", [
    (
        "Senior Data Engineer",
        "Build data pipelines using Spark, Kafka, and Airflow. Need Python, SQL.",
        "Requirement: 5 years experience with Python, Spark, AWS.",
        ['airflow', 'aws', 'kafka', 'python', 'spark', 'sql']
    ),
    (
        "Data Analyst",
        "Use SQL and Power BI for reporting",
        "Need Excel and Python",
        ['excel', 'power bi', 'python', 'sql']
    ),
    (
        "Data Engineer (Junior)",
        "",
        "",
        []
    ),
    (
        "Machine Learning Engineer",
        "Develop ML models using TensorFlow and PyTorch",
        "Experience with Python, scikit-learn",
        ['ml', 'python', 'pytorch', 'scikit-learn', 'tensorflow']  # <-- ĐÃ SỬA
    ),
    (
        "Data Scientist",
        "Use SQL, Python, R for analysis",
        "Familiar with A/B testing and statistics",
        ['python', 'r', 'sql', 'statistics']
    ),
])
def test_extract_skills_parametrize(title, description, requirements, expected):
    """Kiểm tra extract_skills với các ca khác nhau."""
    result = extract_skills(title, description, requirements, SKILL_KEYWORDS)
    assert result == expected


# ==================== TEST VỚI DỮ LIỆU MẪU ====================
def test_extract_skills_with_sample(sample_jobs_all, sample_jobs_detail, sample_jobs_text):
    """
    Kiểm tra extract_skills trên dữ liệu thật từ sample.
    """
    for job_all in sample_jobs_all:
        job_id = job_all.get("id") or job_all.get("url", "").split("/")[-1].replace(".html", "")
        description = None
        requirements = None
        for job_text in sample_jobs_text:
            if job_text.get("id") == job_id:
                description = job_text.get("description")
                requirements = job_text.get("requirements")
                break

        title = job_all.get("title")
        skills = extract_skills(title, description, requirements, SKILL_KEYWORDS)

        assert isinstance(skills, list)
        if title or description or requirements:
            for skill in skills:
                assert isinstance(skill, str)


# ==================== TEST BỔ SUNG ====================
def test_extract_skills_no_false_positive():
    """Kiểm tra không bị false positive với keyword 'r'."""
    title = "Data Engineer"
    description = "Using Spark for data processing"
    requirements = "Need Python and SQL"
    result = extract_skills(title, description, requirements, SKILL_KEYWORDS)
    assert "r" not in result
    assert "spark" in result
    assert "python" in result
    assert "sql" in result


def test_extract_skills_special_chars():
    """Kiểm tra kỹ năng có ký tự đặc biệt (c++, c#, ...)."""
    title = "Senior Developer"
    description = "Need C++ and C# for system programming"
    requirements = ""
    result = extract_skills(title, description, requirements, SKILL_KEYWORDS)
    assert "c++" in result
    assert "c#" in result
    assert "python" not in result


def test_extract_skills_no_false_positive_with_substring():
    """Kiểm tra không bị false positive khi keyword là substring của từ khác."""
    title = "Data Engineer"
    description = "Working with data pipelines"
    requirements = "Need Python and SQL"
    result = extract_skills(title, description, requirements, SKILL_KEYWORDS)
    assert "sql" in result
    assert "data" not in result


def test_extract_skills_with_stopwords():
    """Kiểm tra stopwords không ảnh hưởng đến regex (vẫn bắt đúng kỹ năng)."""
    title = "Data Engineer"
    description = "The candidate must have Python and SQL skills."
    requirements = ""
    result = extract_skills(title, description, requirements, SKILL_KEYWORDS)
    assert "python" in result
    assert "sql" in result