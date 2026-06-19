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
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "jobs_silver.parquet"

    # Chạy pipeline với dữ liệu mẫu (bronze_dir đã có file đúng tên)
    exit_code = run_pipeline(
        bronze_dir=bronze_dir,
        silver_file=output_file,
        output_format="parquet"
    )
    assert exit_code == 0, "Pipeline failed"

    # Kiểm tra file output được tạo
    assert output_file.exists(), "Output file not created"

    # Đọc dữ liệu
    df = pd.read_parquet(output_file)
    assert len(df) > 0, "Output DataFrame is empty"

    # Kiểm tra các cột bắt buộc
    expected_columns = [
        "job_id", "source", "job_url", "title", "company",
        "location_raw", "location_clean",
        "salary_min", "salary_max", "currency", "is_negotiable",
        "exp_min", "exp_max", "deadline", "level", "number_of_hires",
        "job_schedule_type", "working_time", "job_country",
        "work_mode", "job_work_from_home", "seniority_level", "normalized_role",
        "skills", "description", "requirements", "benefits", "crawled_at"
    ]
    for col in expected_columns:
        assert col in df.columns, f"Missing column: {col}"

    # Kiểm tra có ít nhất một bản ghi có normalized_role và location_clean
    assert df["normalized_role"].notna().any(), "No normalized_role found"
    assert df["location_clean"].notna().any(), "No location_clean found"

    # Kiểm tra số lượng bản ghi output khớp với số job trong sample
    all_file = bronze_dir / "jobs_all.json"
    with open(all_file, "r", encoding="utf-8") as f:
        all_jobs = json.load(f)
    assert len(df) >= len(all_jobs), (
        f"Output has {len(df)} records, expected at least {len(all_jobs)}"
    )

    # Kiểm tra một số giá trị cụ thể
    first_title = df.iloc[0]["title"]
    assert first_title is not None and first_title != "", "First job title is empty"