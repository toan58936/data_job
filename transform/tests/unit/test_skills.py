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
        ['machine learning', 'ml', 'python', 'pytorch', 'scikit-learn', 'tensorflow']
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
    # Đối với mỗi job trong all, tìm text tương ứng
    for job_all in sample_jobs_all:
        job_id = job_all.get("id") or job_all.get("url", "").split("/")[-1].replace(".html", "")
        # Tìm text tương ứng
        description = None
        requirements = None
        for job_text in sample_jobs_text:
            if job_text.get("id") == job_id:
                description = job_text.get("description")
                requirements = job_text.get("requirements")
                break

        title = job_all.get("title")
        skills = extract_skills(title, description, requirements, SKILL_KEYWORDS)

        # Kiểm tra: nếu có title/description, skills có thể rỗng nhưng không được None
        assert isinstance(skills, list)
        # Nếu có title hoặc description, ít nhất có thể có skill
        if title or description or requirements:
            # Không bắt buộc phải có skill, nhưng nếu có thì các skill phải là string
            for skill in skills:
                assert isinstance(skill, str)
# Thêm vào cuối file test_skills.py

def test_extract_skills_no_false_positive():
    """Kiểm tra không bị false positive với keyword 'r'."""
    title = "Data Engineer"
    description = "Using Spark for data processing"
    requirements = "Need Python and SQL"
    result = extract_skills(title, description, requirements, SKILL_KEYWORDS)
    # 'r' không xuất hiện ở dạng từ độc lập, nên không được trích xuất
    assert "r" not in result
    assert "spark" in result
    assert "python" in result
    assert "sql" in result