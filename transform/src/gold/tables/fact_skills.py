"""
fact_skills.py - Xây dựng bảng Gold: fact_skills
================================================
Mỗi job được explode thành nhiều row, mỗi row tương ứng với một kỹ năng.
Thêm cột week từ crawled_at.
"""

import pandas as pd
import numpy as np
import logging
import ast
from typing import Optional, List, Union

logger = logging.getLogger(__name__)


def _normalize_skills(skills: Union[List[str], str, np.ndarray, None]) -> List[str]:
    """
    Chuẩn hóa giá trị skills thành list các string.
    Hỗ trợ:
        - list: ['python', 'sql'] -> ['python', 'sql']
        - numpy.ndarray: array(['python', 'sql']) -> ['python', 'sql']
        - string dạng "['python', 'sql']" -> ['python', 'sql']
        - string đơn "python" -> ['python']
        - None hoặc rỗng -> []
    """
    if skills is None:
        return []
    if isinstance(skills, np.ndarray):
        # Chuyển numpy array thành list, lọc bỏ giá trị rỗng
        return [str(s) for s in skills if s and str(s).strip()]
    if isinstance(skills, list):
        return [s for s in skills if s and str(s).strip()]
    if isinstance(skills, str):
        skills_str = skills.strip()
        if not skills_str:
            return []
        if skills_str.startswith('['):
            try:
                parsed = ast.literal_eval(skills_str)
                if isinstance(parsed, list):
                    return [s for s in parsed if s and str(s).strip()]
                return []
            except:
                pass
        return [skills_str]
    # Các kiểu khác (int, float...) -> chuyển thành string
    return [str(skills)] if pd.notna(skills) else []


def build_fact_skills(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tạo bảng fact_skills từ Silver DataFrame.

    Args:
        df: DataFrame Silver (có các cột: job_id, skills, normalized_role, salary_max, crawled_at)

    Returns:
        DataFrame với các cột:
            - job_id: ID của job
            - skill: Tên kỹ năng (mỗi row một skill)
            - normalized_role: Role chuẩn hóa
            - salary_max: Mức lương tối đa
            - week: Tuần trong năm (tính từ crawled_at)
    """
    required_cols = ['job_id', 'skills', 'normalized_role', 'salary_max', 'crawled_at']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # 1. Chuẩn hóa skills thành list cho từng row
    df_copy = df.copy()
    df_copy['skills_normalized'] = df_copy['skills'].apply(_normalize_skills)

    # 2. Lọc bỏ các job không có skills (rỗng)
    mask = df_copy['skills_normalized'].apply(lambda x: len(x) > 0)
    df_filtered = df_copy[mask].copy()

    if df_filtered.empty:
        logger.warning("No jobs with skills found. Returning empty fact_skills DataFrame.")
        return pd.DataFrame(columns=['job_id', 'skill', 'normalized_role', 'salary_max', 'week'])

    # 3. Explode skills -> mỗi skill là một row
    df_exploded = df_filtered.explode('skills_normalized')
    df_exploded = df_exploded.rename(columns={'skills_normalized': 'skill'})

    # 4. Xử lý crawled_at -> tính week
    if not pd.api.types.is_datetime64_any_dtype(df_exploded['crawled_at']):
        df_exploded['crawled_at'] = pd.to_datetime(df_exploded['crawled_at'])

    if df_exploded['crawled_at'].dt.tz is not None:
        df_exploded['crawled_at'] = df_exploded['crawled_at'].dt.tz_convert(None)

    df_exploded['week'] = df_exploded['crawled_at'].dt.isocalendar().week

    # 5. Chọn các cột cần giữ lại
    result = df_exploded[['job_id', 'skill', 'normalized_role', 'salary_max', 'week']].copy()

    logger.info(f"fact_skills built: {len(result)} rows from {len(df_filtered)} jobs")
    return result