"""
pipeline.py - Điều phối luồng xử lý Transform
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import các module của pipeline
from transform.src.io.reader import merge_data
from transform.src.io.writer import write_silver
from transform.src.processors.location import clean_location
from transform.src.processors.experience import parse_experience
from transform.src.processors.salary import parse_salary
from transform.src.processors.skills import extract_skills
from transform.src.processors.role import normalize_role
from transform.src.processors.work_mode import derive_work_mode
from transform.src.processors.seniority import derive_seniority
from transform.src.processors.domain import extract_domain_keywords
from ..utils.config import SKILL_KEYWORDS, JOB_SCHEDULE_MAPPING, DOMAIN_KEYWORDS
from transform.src.schemas.silver_schema import SilverJob

# === TÍCH HỢP DATA QUALITY ===
from ..quality.runner import run_quality
from ..utils.config_loader import load_config

# === TÍCH HỢP GOLD ===
from transform.src.gold.gold_builder import build_gold

# Cấu hình logging
logger = logging.getLogger(__name__)


def process_record(record: Dict[str, Any]) -> SilverJob:
    """
    Áp dụng tất cả các processor lên một bản ghi thô, trả về đối tượng SilverJob.
    """
    # ── Field names sau source_normalizer ──────────────────────────────
    # source_normalizer.py đổi tên các field thô về contract chuẩn:
    #   location   → location_raw      (tránh xung đột với location_clean)
    #   salary     → salary_raw        (TopCV: text thô; ITviec: None nếu có pre-parsed)
    #   experience → experience_raw
    # pipeline.py phải đọc đúng tên đã chuẩn hóa này.
    # ───────────────────────────────────────────────────────────────────

    # 1. Location — đọc location_raw (đã chuẩn hóa bởi normalizer)
    location_clean = clean_location(record.get('location_raw'))

    # 2. Experience — đọc experience_raw
    exp_raw = record.get('experience_raw')
    exp_min, exp_max = parse_experience(exp_raw)

    # 3. Salary — ưu tiên pre-parsed (ITviec detail đã có salary_min/max)
    #    nếu không có thì parse từ salary_raw text (TopCV)
    salary_pre = record.get('salary_pre_parsed')
    if salary_pre and (salary_pre.get('min') is not None or salary_pre.get('max') is not None):
        salary_info = {
            'salary_min':    salary_pre.get('min'),
            'salary_max':    salary_pre.get('max'),
            'currency':      salary_pre.get('currency'),
            'is_negotiable': salary_pre.get('is_negotiable', False),
        }
    else:
        salary_info = parse_salary(record.get('salary_raw'))

    # 4. Skills — ưu tiên skills_pre_extracted (ITviec listing đã extract)
    skills = extract_skills(
        title=record.get('title'),
        description=record.get('description'),
        requirements=record.get('requirements'),
        skill_keywords=SKILL_KEYWORDS,
        pre_extracted=record.get('skills_pre_extracted'),
    )

    # 5. Domain keywords
    domain_keywords = extract_domain_keywords(
        title=record.get('title'),
        description=record.get('description'),
        requirements=record.get('requirements'),
        domain_keywords=DOMAIN_KEYWORDS,
    )

    # 6. Role
    normalized_role = normalize_role(record.get('title'))

    # 7. Seniority
    seniority_level = derive_seniority(record.get('title'), exp_min)

    # 8. Work mode — ITviec dùng 'work_model', TopCV dùng 'working_time'
    work_mode, job_work_from_home = derive_work_mode(
        working_time=record.get('working_time') or record.get('work_model'),
        description=record.get('description'),
        requirements=record.get('requirements'),
    )

    # 9. Job schedule type
    job_type_raw = record.get('job_type')
    job_schedule_type = JOB_SCHEDULE_MAPPING.get(job_type_raw, None)

    # 10. Tạo đối tượng SilverJob
    silver_job = SilverJob(
        job_id=record.get('job_id'),
        source=record.get('source', 'Unknown'),
        job_url=record.get('job_url'),
        title=record.get('title'),
        company=record.get('company'),
        location_raw=record.get('location_raw'),
        location_clean=location_clean,
        salary_min=salary_info['salary_min'],
        salary_max=salary_info['salary_max'],
        currency=salary_info['currency'],
        is_negotiable=salary_info['is_negotiable'],
        exp_min=exp_min,
        exp_max=exp_max,
        deadline=record.get('deadline'),
        level=record.get('level'),
        number_of_hires=record.get('number_of_hires'),
        job_schedule_type=job_schedule_type,
        working_time=record.get('working_time') or record.get('work_model'),
        job_country="Vietnam",
        work_mode=work_mode,
        job_work_from_home=job_work_from_home,
        seniority_level=seniority_level,
        normalized_role=normalized_role,
        skills=skills,
        domain_keywords=domain_keywords,
        description=record.get('description'),
        requirements=record.get('requirements'),
        benefits=record.get('benefits'),
        crawled_at=record.get('crawled_at'),
    )
    return silver_job


def run_pipeline(
    bronze_dir: Optional[Path] = None,
    silver_file: Optional[Path] = None,
    output_format: str = "parquet",
    run_quality_checks: bool = True,
    run_gold: bool = True
) -> int:
    """
    Chạy toàn bộ pipeline Transform.

    Args:
        bronze_dir: Đường dẫn đến thư mục Bronze (mặc định: ./data/bronze)
        silver_file: Đường dẫn đến file Silver output (mặc định: ./data/silver/jobs_silver.parquet)
        output_format: "parquet" hoặc "csv"
        run_quality_checks: Nếu True, chạy Data Quality sau transform.
        run_gold: Nếu True, chạy Gold builder sau transform.

    Returns:
        int: 0 nếu thành công, khác 0 nếu lỗi.
    """
    logger.info("=" * 60)
    logger.info("Starting Silver Transform Pipeline")
    logger.info("=" * 60)

    # 1. Xác định đường dẫn mặc định
    project_root = Path(__file__).parent.parent.parent.parent
    if bronze_dir is None:
        bronze_dir = project_root / "data" / "bronze"
    if silver_file is None:
        silver_dir = project_root / "data" / "silver"
        silver_dir.mkdir(parents=True, exist_ok=True)
        if output_format == "parquet":
            silver_file = silver_dir / "jobs_silver.parquet"
        else:
            silver_file = silver_dir / "jobs_silver.csv"

    logger.info(f"Bronze directory: {bronze_dir}")
    logger.info(f"Silver output: {silver_file}")

    # 2. Đọc và hợp nhất dữ liệu
    try:
        raw_records = merge_data(bronze_dir)
    except Exception as e:
        logger.error(f"Failed to read/merge data: {e}")
        return 1

    if not raw_records:
        logger.warning("No records found. Pipeline will exit.")
        return 0

    logger.info(f"Total raw records: {len(raw_records)}")

    # 3. Xử lý từng bản ghi
    silver_records: List[SilverJob] = []
    errors = 0
    for idx, record in enumerate(raw_records, 1):
        try:
            silver_job = process_record(record)
            silver_records.append(silver_job)
            if idx % 10 == 0:
                logger.info(f"Processed {idx}/{len(raw_records)} records")
        except Exception as e:
            logger.error(f"Error processing record {idx} (URL: {record.get('url')}): {e}")
            errors += 1

    logger.info(f"Processed {len(silver_records)} records successfully, {errors} errors.")

    if not silver_records:
        logger.warning("No records processed successfully. Pipeline exits.")
        return 1

    # 4. Ghi kết quả
    try:
        write_silver(silver_records, silver_file, format=output_format)
        logger.info(f"Silver data written to {silver_file}")
    except Exception as e:
        logger.error(f"Failed to write silver data: {e}")
        return 1

    # ============================================================
    # === TÍCH HỢP DATA QUALITY ===
    # ============================================================
    if run_quality_checks:
        try:
            config = load_config()
            quality_config = config.get('quality', {})
            enabled_stages = quality_config.get('enabled_stages', [])

            if enabled_stages:
                logger.info("Running Data Quality checks after transform...")
                exit_code = run_quality(
                    silver_file=silver_file,
                    output_dir=Path(quality_config.get('report_dir', 'data/quality')),
                    stages=enabled_stages,
                    silent=False,
                    config=quality_config
                )
                if exit_code != 0 and quality_config.get('stop_on_error', True):
                    logger.error("Data Quality checks failed. Pipeline stopped.")
                    return exit_code
                else:
                    logger.info("Data Quality checks completed.")
            else:
                logger.info("Data Quality checks are disabled in config. Skipping.")
        except Exception as e:
            logger.error(f"Error running Data Quality: {e}")
            logger.warning("Data Quality encountered an error but pipeline continues.")
    else:
        logger.info("Data Quality checks are disabled (run_quality_checks=False).")

    # ============================================================
    # === TÍCH HỢP GOLD ===
    # ============================================================
    if run_gold:
        try:
            config = load_config()
            gold_config = config.get('gold', {})
            if gold_config.get('enabled', True):
                gold_dir = Path(gold_config.get('output_dir', 'data/gold'))
                logger.info(f"Building Gold layer at {gold_dir}...")
                exit_code = build_gold(silver_file, gold_dir)
                if exit_code != 0:
                    logger.error("Gold build failed. Check logs for details.")
                    logger.warning("Gold layer was not built successfully, but pipeline continues.")
                else:
                    logger.info("Gold layer built successfully.")
            else:
                logger.info("Gold builder is disabled in config. Skipping.")
        except Exception as e:
            logger.error(f"Error building Gold: {e}")
            logger.warning("Gold layer encountered an error but pipeline continues.")
    else:
        logger.info("Gold builder is disabled (run_gold=False).")

    # ============================================================
    # Kết thúc pipeline
    logger.info("=" * 60)
    logger.info("Silver Transform Pipeline completed successfully!")
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(run_pipeline())