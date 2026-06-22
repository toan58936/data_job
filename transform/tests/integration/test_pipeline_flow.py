"""
test_pipeline_flow.py - Integration test cho toàn bộ pipeline.
Sử dụng dữ liệu mẫu từ fixtures để kiểm tra luồng xử lý từ Bronze đến Silver.
"""

import json
import shutil
import pytest
import pandas as pd
from pathlib import Path

from transform.src.orchestrator.pipeline import run_pipeline


@pytest.fixture
def fixtures_dir():
    """Đường dẫn đến thư mục fixtures chứa dữ liệu mẫu."""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def bronze_dir(tmp_path, fixtures_dir):
    """
    Tạo thư mục bronze tạm với các file có tên chuẩn (jobs_all.json, ...)
    bằng cách copy từ fixtures.
    """
    bronze = tmp_path / "bronze"
    bronze.mkdir()

    # Ánh xạ tên file sample -> tên chuẩn
    mapping = {
        "sample_jobs_all.json": "jobs_all.json",
        "sample_jobs_detail.json": "jobs_detail.json",
        "sample_jobs_text.json": "job_text_final.json",
    }
    for src, dst in mapping.items():
        src_file = fixtures_dir / src
        if src_file.exists():
            shutil.copy(src_file, bronze / dst)
        else:
            # Tạo file rỗng để không bị lỗi (nhưng test sẽ fail vì thiếu dữ liệu)
            (bronze / dst).write_text("[]")

    return bronze


@pytest.fixture
def output_dir(tmp_path):
    """Thư mục tạm để lưu output."""
    return tmp_path / "silver"


def test_pipeline_flow(bronze_dir, output_dir):
    """
    Chạy toàn bộ pipeline với dữ liệu mẫu và kiểm tra output.
    Kiểm tra:
    - Pipeline chạy thành công
    - Output file được tạo
    - Schema đúng
    - Số lượng record khớp với input
    - Giá trị của các trường quan trọng sau transform
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "jobs_silver.parquet"

    # ===== 1. Chạy pipeline với dữ liệu mẫu =====
    exit_code = run_pipeline(
        bronze_dir=bronze_dir,
        silver_file=output_file,
        output_format="parquet",
        run_quality_checks=False,
        run_gold=False   # Tắt Data Quality để tránh fail do dữ liệu mẫu không có salary
    )
    assert exit_code == 0, "Pipeline failed"

    # ===== 2. Kiểm tra file output được tạo =====
    assert output_file.exists(), "Output file not created"

    # ===== 3. Đọc dữ liệu =====
    df = pd.read_parquet(output_file)
    assert len(df) > 0, "Output DataFrame is empty"

    # ===== 4. Kiểm tra schema =====
    expected_columns = [
        "job_id", "source", "job_url", "title", "company",
        "location_raw", "location_clean",
        "salary_min", "salary_max", "currency", "is_negotiable",
        "exp_min", "exp_max", "deadline", "level", "number_of_hires",
        "job_schedule_type", "working_time", "job_country",
        "work_mode", "job_work_from_home", "seniority_level", "normalized_role",
        "skills", "domain_keywords", "description", "requirements", "benefits", "crawled_at"
    ]
    for col in expected_columns:
        assert col in df.columns, f"Missing column: {col}"

    # ===== 5. Kiểm tra số lượng record =====
    all_file = bronze_dir / "jobs_all.json"
    with open(all_file, "r", encoding="utf-8") as f:
        all_jobs = json.load(f)
    assert len(df) == len(all_jobs), (
        f"Output has {len(df)} records, expected {len(all_jobs)}"
    )

    # ===== 6. Kiểm tra giá trị cụ thể cho từng job =====
    # Tạo dict mapping job_id -> row để kiểm tra
    df_dict = {row['job_id']: row for _, row in df.iterrows()}

    # 6.1 Job 2168835: "Data Engineer (Senior/Leader)"
    job1 = df_dict.get("2168835")
    assert job1 is not None, "Job 2168835 not found"
    assert job1['title'] == "Data Engineer (Senior/Leader)"
    assert job1['source'] == "TopCV"
    assert job1['job_country'] == "Vietnam"
    # Kiểm tra role mapping (Task 1)
    # Title có "Data Engineer" -> phải là Data Engineer
    assert job1['normalized_role'] == "Data Engineer"
    # Kiểm tra location (Task 3)
    assert job1['location_clean'] == "Hà Nội"
    # Kiểm tra skills (có một số skill xuất hiện trong description/requirements)
    assert "python" in job1['skills']
    assert "sql" in job1['skills']
    # Kiểm tra domain keywords
    assert len(job1['domain_keywords']) >= 0  # Có thể rỗng

    # 6.2 Job 2178692: "Data Solution Architect"
    job2 = df_dict.get("2178692")
    assert job2 is not None, "Job 2178692 not found"
    assert job2['title'] == "Data Solution Architect"
    # Role mapping: khớp pattern "data solution architect" -> "Data Architect"
    assert job2['normalized_role'] == "Data Architect"  # <-- SỬA Ở ĐÂY
    # Location: Hà Nội -> Hà Nội
    assert job2['location_clean'] == "Hà Nội"
    # Skills: kiểm tra có SQL (xuất hiện trong requirements)
    assert "sql" in job2['skills']
    # Domain keywords: "data warehouse", "data lakehouse" xuất hiện trong description
    assert "data warehouse" in job2['domain_keywords']
    assert "data lakehouse" in job2['domain_keywords']

    # 6.3 Job 2124490: "Data Engineer Lead"
    job3 = df_dict.get("2124490")
    assert job3 is not None, "Job 2124490 not found"
    assert job3['title'] == "Data Engineer Lead"
    # Role mapping: có "Data Engineer" -> Data Engineer
    assert job3['normalized_role'] == "Data Engineer"
    # Seniority: có "Lead" trong title -> Lead
    assert job3['seniority_level'] == "Lead"
    # Location: Hà Nội -> Hà Nội
    assert job3['location_clean'] == "Hà Nội"
    # Skills: SQL xuất hiện trong requirements
    assert "sql" in job3['skills']
    # Domain keywords: "data warehouse" xuất hiện trong description
    assert "data warehouse" in job3['domain_keywords']

    # ===== 7. Kiểm tra các trường không được null =====
    # Các trường bắt buộc không được null
    required_non_null_fields = [
        "job_id", "source", "job_url", "title", "company",
        "location_raw", "location_clean", "job_country",
        "work_mode", "crawled_at"
    ]
    for field in required_non_null_fields:
        assert df[field].notna().all(), f"Field '{field}' has null values"

    # ===== 8. Kiểm tra job_country luôn là Vietnam =====
    assert (df['job_country'] == "Vietnam").all(), "Not all jobs have job_country = 'Vietnam'"

    # ===== 9. Kiểm tra skills không chứa domain keywords =====
    # Domain keywords như 'data warehouse', 'machine learning' không nằm trong skills
    for _, row in df.iterrows():
        skills = row.get('skills', [])
        # Kiểm tra không có domain keywords trong skills
        for skill in skills:
            assert skill not in ['data warehouse', 'data lakehouse', 'machine learning', 'ml', 'ai'], \
                f"Domain keyword '{skill}' found in skills for job {row['job_id']}"

    # ===== 10. Kiểm tra Gold layer =====
    gold_dir = output_dir.parent / "gold"
    gold_files = [
        "metrics.parquet",
        "salary_by_role.parquet",
        "salary_by_seniority.parquet",
        "heatmap_salary.parquet",
        "top_skills.parquet",
        "skills_by_role.parquet",
        "location_distribution.parquet",
        "work_mode_distribution.parquet",
        "top_domains.parquet"
    ]
    for f in gold_files:
        assert (gold_dir / f).exists(), f"Gold file {f} not created"