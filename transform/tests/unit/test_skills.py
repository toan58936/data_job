"""
test_skills.py - Unit test cho processor skills
"""
import pytest
from transform.src.processors.skills import extract_skills
from transform.src.utils.config import SKILL_KEYWORDS


# ==================== TEST VỚI PARAMETRIZE ====================
# ==================== TEST PRE-EXTRACTED SKILLS (ITviec) ====================
@pytest.mark.parametrize("pre_extracted, expected", [
    (
        ['Python', 'SQL', 'Spark', 'AWS'],
        ['aws', 'python', 'spark', 'sql']
    ),
    (
        ['Machine Learning', 'Python', 'TensorFlow'],
        ['python', 'tensorflow']   # 'machine learning' bị loại vì là domain
    ),
    (
        ['Data Engineer', 'SQL', 'ETL'],
        ['etl', 'sql']             # 'Data Engineer' không nằm trong SKILL_KEYWORDS
    ),
    (
        [],
        []
    ),
])
def test_extract_skills_pre_extracted(pre_extracted, expected):
    """
    Kiểm tra pre_extracted skills từ ITviec.
    - Nếu có pre_extracted, bỏ qua title/description/requirements
    - Lọc bỏ domain keywords và chỉ giữ những skill có trong SKILL_KEYWORDS
    """
    title = "Some Data Engineer Job"
    description = "Build data pipelines using Python and Spark"
    requirements = "Need Python and SQL"
    result = extract_skills(
        title=title,
        description=description,
        requirements=requirements,
        skill_keywords=SKILL_KEYWORDS,
        pre_extracted=pre_extracted
    )
    assert result == expected

# ==================== TEST PRE-EXTRACTED SKILLS (ITviec) ====================
@pytest.mark.parametrize("pre_extracted, expected", [
    (
        ['Python', 'SQL', 'Spark', 'AWS'],
        ['aws', 'python', 'spark', 'sql']
    ),
    (
        ['Machine Learning', 'Python', 'TensorFlow'],
        ['python', 'tensorflow']
    ),
    (
        ['Data Engineer', 'SQL', 'ETL'],
        ['sql']
    ),
    (
        [],
        []
    ),
])
def test_extract_skills_pre_extracted(pre_extracted, expected):
    """
    Kiểm tra pre_extracted skills từ ITviec.
    - Nếu có pre_extracted, bỏ qua title/description/requirements
    - Lọc bỏ domain keywords
    """
    title = "Some Data Engineer Job"
    description = "Build data pipelines using Python and Spark"
    requirements = "Need Python and SQL"
    result = extract_skills(
        title=title,
        description=description,
        requirements=requirements,
        skill_keywords=SKILL_KEYWORDS,
        pre_extracted=pre_extracted
    )
    assert result == expected


# ==================== TEST PRE-EXTRACTED KHÔNG ẢNH HƯỞNG TOPCV ====================
def test_extract_skills_pre_extracted_none():
    """
    Kiểm tra khi không có pre_extracted, vẫn extract từ text như cũ.
    """
    title = "Data Engineer"
    description = "Using Spark for data processing"
    requirements = "Need Python and SQL"
    result = extract_skills(
        title=title,
        description=description,
        requirements=requirements,
        skill_keywords=SKILL_KEYWORDS,
        pre_extracted=None
    )
    assert "python" in result
    assert "sql" in result
    assert "spark" in result


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