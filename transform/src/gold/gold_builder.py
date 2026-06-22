"""
gold_builder.py - Xây dựng các bảng Gold từ Silver
Mỗi bảng là một insight đã được tính toán sẵn.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def _to_list(x):
    """Chuyển đổi an toàn sang list."""
    if isinstance(x, list):
        return x
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, str):
        try:
            import ast
            return ast.literal_eval(x) if x.startswith('[') else []
        except:
            return []
    return []


def build_gold(silver_path: Path, gold_dir: Path) -> int:
    """
    Đọc Silver, tính toán các insight và ghi ra Gold.

    Args:
        silver_path: Đường dẫn đến file Parquet Silver.
        gold_dir: Thư mục lưu các bảng Gold.

    Returns:
        int: 0 nếu thành công, khác 0 nếu lỗi.
    """
    try:
        logger.info("Đọc Silver từ %s", silver_path)
        df = pd.read_parquet(silver_path)
        logger.info("Đọc được %d dòng", len(df))

        # Chuẩn hóa cột skills và domain_keywords
        df['skills'] = df['skills'].apply(_to_list)
        df['domain_keywords'] = df['domain_keywords'].apply(_to_list)

        # Tạo thư mục gold nếu chưa có
        gold_dir.mkdir(parents=True, exist_ok=True)

        # ==================== 1. Metrics ====================
        metrics = {
            'total_jobs': len(df),
            'avg_salary_max': df['salary_max'].mean() if not df['salary_max'].isna().all() else None,
            'top_role': df['normalized_role'].value_counts().idxmax() if not df.empty else None,
            'top_location': df['location_clean'].value_counts().idxmax() if not df.empty else None,
        }
        metrics_df = pd.DataFrame([metrics])
        metrics_df.to_parquet(gold_dir / 'metrics.parquet', index=False)
        logger.info("Saved metrics.parquet")

        # ==================== 2. Salary by Role ====================
        salary_by_role = df.groupby('normalized_role').agg(
            salary_min_mean=('salary_min', 'mean'),
            salary_max_mean=('salary_max', 'mean')
        ).reset_index().dropna()
        if not salary_by_role.empty:
            salary_by_role.to_parquet(gold_dir / 'salary_by_role.parquet', index=False)
        else:
            # Tạo DataFrame rỗng với đúng schema
            pd.DataFrame(columns=['normalized_role', 'salary_min_mean', 'salary_max_mean']) \
                .to_parquet(gold_dir / 'salary_by_role.parquet', index=False)
        logger.info("Saved salary_by_role.parquet")

        # ==================== 3. Salary by Seniority ====================
        salary_by_seniority = df.groupby('seniority_level').agg(
            salary_max_mean=('salary_max', 'mean')
        ).reset_index().dropna()
        if not salary_by_seniority.empty:
            salary_by_seniority.to_parquet(gold_dir / 'salary_by_seniority.parquet', index=False)
        else:
            pd.DataFrame(columns=['seniority_level', 'salary_max_mean']) \
                .to_parquet(gold_dir / 'salary_by_seniority.parquet', index=False)
        logger.info("Saved salary_by_seniority.parquet")

        # ==================== 4. Heatmap Salary (Role x Seniority) ====================
        heatmap = df.pivot_table(
            index='normalized_role',
            columns='seniority_level',
            values='salary_max',
            aggfunc='mean'
        ).reset_index()
        # Lưu dưới dạng long format để dễ vẽ
        heatmap_long = heatmap.melt(id_vars='normalized_role', var_name='seniority_level', value_name='salary_max_mean')
        heatmap_long = heatmap_long.dropna()
        if not heatmap_long.empty:
            heatmap_long.to_parquet(gold_dir / 'heatmap_salary.parquet', index=False)
        else:
            pd.DataFrame(columns=['normalized_role', 'seniority_level', 'salary_max_mean']) \
                .to_parquet(gold_dir / 'heatmap_salary.parquet', index=False)
        logger.info("Saved heatmap_salary.parquet")

        # ==================== 5. Top 20 Skills ====================
        all_skills = []
        for skills in df['skills']:
            all_skills.extend(skills)
        skill_counts = Counter(all_skills)
        top_skills = skill_counts.most_common(20)
        if top_skills:
            skills_df = pd.DataFrame(top_skills, columns=['skill', 'count'])
            skills_df.to_parquet(gold_dir / 'top_skills.parquet', index=False)
        else:
            pd.DataFrame(columns=['skill', 'count']).to_parquet(gold_dir / 'top_skills.parquet', index=False)
        logger.info("Saved top_skills.parquet")

        # ==================== 6. Skills by Role (Top 5 per role) ====================
        if not df.empty and 'skills' in df.columns:
            exploded = df.explode('skills')
            role_skill = exploded.groupby(['normalized_role', 'skills']).size().reset_index(name='count')
            top_role_skills = role_skill.sort_values(['normalized_role', 'count'], ascending=[True, False]) \
                                       .groupby('normalized_role').head(5)
            if not top_role_skills.empty:
                top_role_skills.to_parquet(gold_dir / 'skills_by_role.parquet', index=False)
            else:
                pd.DataFrame(columns=['normalized_role', 'skills', 'count']) \
                    .to_parquet(gold_dir / 'skills_by_role.parquet', index=False)
            logger.info("Saved skills_by_role.parquet")

        # ==================== 7. Location Distribution ====================
        location_counts = df['location_clean'].value_counts().reset_index()
        location_counts.columns = ['location', 'count']
        if not location_counts.empty:
            location_counts.to_parquet(gold_dir / 'location_distribution.parquet', index=False)
        else:
            pd.DataFrame(columns=['location', 'count']).to_parquet(gold_dir / 'location_distribution.parquet', index=False)
        logger.info("Saved location_distribution.parquet")

        # ==================== 8. Work Mode Distribution ====================
        work_mode_counts = df['work_mode'].value_counts().reset_index()
        work_mode_counts.columns = ['work_mode', 'count']
        if not work_mode_counts.empty:
            work_mode_counts.to_parquet(gold_dir / 'work_mode_distribution.parquet', index=False)
        else:
            pd.DataFrame(columns=['work_mode', 'count']).to_parquet(gold_dir / 'work_mode_distribution.parquet', index=False)
        logger.info("Saved work_mode_distribution.parquet")

        # ==================== 9. Top 15 Domain Keywords ====================
        all_domains = []
        for domains in df['domain_keywords']:
            all_domains.extend(domains)
        domain_counts = Counter(all_domains)
        top_domains = domain_counts.most_common(15)
        if top_domains:
            domain_df = pd.DataFrame(top_domains, columns=['domain', 'count'])
            domain_df.to_parquet(gold_dir / 'top_domains.parquet', index=False)
        else:
            pd.DataFrame(columns=['domain', 'count']).to_parquet(gold_dir / 'top_domains.parquet', index=False)
        logger.info("Saved top_domains.parquet")

        logger.info("✅ Gold builder finished successfully.")
        return 0

    except Exception as e:
        logger.error(f"❌ Gold builder failed: {e}")
        return 1


if __name__ == "__main__":
    # Test khi chạy trực tiếp
    import sys
    silver = Path("data/silver/jobs_silver.parquet")
    gold = Path("data/gold")
    sys.exit(build_gold(silver, gold))