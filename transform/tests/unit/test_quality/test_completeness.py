import pandas as pd
import pytest
from transform.src.quality.completeness import check_completeness


def test_completeness_all_ok():
    df = pd.DataFrame({
        'title': ['Job1', 'Job2'],
        'company': ['Company A', 'Company B'],
        'location_clean': ['Hà Nội', 'Hồ Chí Minh'],
        'normalized_role': ['Data Engineer', 'Data Analyst'],
        'salary_min': [10.0, 20.0],
        'salary_max': [15.0, 25.0],
        'skills': [['python'], ['sql', 'spark']],
        'deadline': ['2026-12-31', '2026-12-31']
    })
    result = check_completeness(df)
    for field, data in result.items():
        assert data['status'] == 'OK'
        assert data['percentage'] == 100.0


def test_completeness_missing_data():
    df = pd.DataFrame({
        'title': ['Job1', None],
        'company': ['Company A', ''],
        'location_clean': ['Hà Nội', None],
        'normalized_role': ['Data Engineer', 'Data Analyst'],
        'salary_min': [10.0, None],
        'salary_max': [15.0, None],  # <-- SỬA: thêm None để tỷ lệ 50%
        'skills': [[], None],
        'deadline': ['2026-12-31', None]
    })
    result = check_completeness(df)

    # title: 1/2 = 50% -> ERROR (dùng ngưỡng chung 80%)
    assert result['title']['percentage'] == 50.0
    assert result['title']['status'] == 'ERROR'

    # salary_min: 1/2 = 50% -> WARNING (vì override ngưỡng 50%)
    assert result['salary_min']['percentage'] == 50.0
    assert result['salary_min']['status'] == 'WARNING'

    # salary_max: 1/2 = 50% -> WARNING
    assert result['salary_max']['percentage'] == 50.0
    assert result['salary_max']['status'] == 'WARNING'

    # deadline: 1/2 = 50% -> ERROR (dùng ngưỡng chung)
    assert result['deadline']['percentage'] == 50.0
    assert result['deadline']['status'] == 'ERROR'


def test_completeness_warning_level():
    df = pd.DataFrame({
        'title': ['Job' + str(i) for i in range(7)],
        'company': ['A'] * 7,
        'location_clean': ['Hà Nội'] * 6 + [None],  # 6/7 = 85.71%
        'normalized_role': ['DE'] * 7,
        'salary_min': [10.0] * 7,
        'salary_max': [15.0] * 7,
        'skills': [['python']] * 7,
        'deadline': ['2026-12-31'] * 7
    })
    result = check_completeness(df)
    assert result['location_clean']['percentage'] == pytest.approx(85.71, 0.1)
    assert result['location_clean']['status'] == 'WARNING'


def test_completeness_empty_dataframe():
    df = pd.DataFrame()
    result = check_completeness(df)
    assert result == {}


def test_completeness_missing_column():
    df = pd.DataFrame({
        'title': ['Job1'],
        'company': ['A'],
    })
    result = check_completeness(df)
    assert result['location_clean']['percentage'] == 0.0
    assert result['location_clean']['status'] == 'ERROR'
    assert result['salary_min']['percentage'] == 0.0
    # 0% < 50% nên vẫn là ERROR (không phải WARNING)
    assert result['salary_min']['status'] == 'ERROR'


def test_completeness_skills_various_types():
    df = pd.DataFrame({
        'title': ['Job1', 'Job2', 'Job3', 'Job4'],
        'company': ['A'] * 4,
        'location_clean': ['HN'] * 4,
        'normalized_role': ['DE'] * 4,
        'salary_min': [10.0] * 4,
        'salary_max': [15.0] * 4,
        'skills': [
            ['python', 'sql'],
            [],
            "['python']",
            None
        ],
        'deadline': ['2026-12-31'] * 4
    })
    result = check_completeness(df)
    # skills: 2/4 = 50% -> ERROR (vì không override, dùng ngưỡng 80%)
    assert result['skills']['percentage'] == 50.0
    assert result['skills']['status'] == 'ERROR'


def test_completeness_skills_string_empty_and_brackets():
    df = pd.DataFrame({
        'title': ['Job1', 'Job2', 'Job3'],
        'company': ['A'] * 3,
        'location_clean': ['HN'] * 3,
        'normalized_role': ['DE'] * 3,
        'salary_min': [10.0] * 3,
        'salary_max': [15.0] * 3,
        'skills': [
            '',
            '[]',
            '["python"]'
        ],
        'deadline': ['2026-12-31'] * 3
    })
    result = check_completeness(df)
    # skills: 1/3 = 33.33% -> ERROR (dùng ngưỡng 80%)
    assert result['skills']['percentage'] == pytest.approx(33.33, 0.1)
    assert result['skills']['status'] == 'ERROR'