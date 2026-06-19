"""
runner.py - Điều phối toàn bộ quy trình Data Quality.
Chạy các stage, tổng hợp kết quả, gọi reporter và xác định exit code.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

import pandas as pd
import typer

from .completeness import check_completeness
from .validity import check_validity
from .accuracy import check_accuracy
from .uniqueness import check_uniqueness
from .timeliness import check_timeliness
from .reporter import save_report, print_console
from ..utils.config_loader import load_config


# Đăng ký các stage
STAGE_REGISTRY = {
    'completeness': {
        'func': check_completeness,
        'description': 'Kiểm tra tính đầy đủ của các trường quan trọng'
    },
    'validity': {
        'func': check_validity,
        'description': 'Kiểm tra tính hợp lệ theo ràng buộc logic'
    },
    'accuracy': {
        'func': check_accuracy,
        'description': 'Kiểm tra tính chính xác (outlier, lương thỏa thuận...)'
    },
    'uniqueness': {
        'func': check_uniqueness,
        'description': 'Kiểm tra trùng lặp và nhất quán giữa role và title'
    },
    'timeliness': {
        'func': check_timeliness,
        'description': 'Kiểm tra tính kịp thời của dữ liệu'
    }
}


def run_quality(
    silver_file: Path,
    output_dir: Optional[Path] = None,
    stages: Optional[List[str]] = None,
    silent: bool = False,
    config: Optional[Dict[str, Any]] = None
) -> int:
    """
    Chạy các stage kiểm tra chất lượng dữ liệu.

    Args:
        silver_file: Đường dẫn đến file Silver Parquet.
        output_dir: Thư mục lưu báo cáo (mặc định: data/quality).
        stages: Danh sách stage cần chạy (mặc định: tất cả).
        silent: Nếu True, không in ra console (chỉ lưu file).
        config: Dict chứa cấu hình quality (từ config.yaml). Nếu None, tự động load.

    Returns:
        int: 0 nếu không có lỗi, 1 nếu có lỗi.
    """
    # 1. Nếu config chưa được truyền, load từ file config
    if config is None:
        full_config = load_config()
        config = full_config.get('quality', {})

    # 2. Kiểm tra file đầu vào
    if not silver_file.exists():
        typer.secho(f"❌ Không tìm thấy file Silver: {silver_file}", fg=typer.colors.RED, err=True)
        return 1

    # 3. Đọc dữ liệu
    try:
        df = pd.read_parquet(silver_file)
    except Exception as e:
        typer.secho(f"❌ Lỗi đọc Parquet: {e}", fg=typer.colors.RED, err=True)
        return 1

    if df.empty:
        typer.secho("⚠️ DataFrame rỗng, không có dữ liệu để kiểm tra.", fg=typer.colors.YELLOW)
        return 0

    # 4. Xác định danh sách stage cần chạy
    all_stage_names = list(STAGE_REGISTRY.keys())
    if stages is None:
        # Nếu không chỉ định stage, lấy từ config hoặc tất cả
        stages_to_run = config.get('enabled_stages', all_stage_names)
    else:
        # Lọc theo danh sách chỉ định, bỏ qua stage không tồn tại
        stages_to_run = [s for s in stages if s in STAGE_REGISTRY]
        if not stages_to_run:
            typer.secho("⚠️ Không có stage hợp lệ nào được chỉ định.", fg=typer.colors.YELLOW)
            return 1

    # 5. Chuẩn bị các tham số cho từng stage từ config
    # Lấy ngưỡng completeness
    comp_config = config.get('completeness', {})
    warning_threshold = comp_config.get('warning_threshold', 0.95)
    error_threshold = comp_config.get('error_threshold', 0.80)
    field_error_thresholds = comp_config.get('field_overrides', {})

    # Các stage khác có thể lấy ngưỡng nếu cần (hiện tại chưa hỗ trợ)

    # 6. Chạy từng stage
    results = {}
    has_error = False
    for stage_name in stages_to_run:
        func = STAGE_REGISTRY[stage_name]['func']
        if not silent:
            typer.secho(f"\n🔄 Đang chạy stage: {stage_name}...", fg=typer.colors.CYAN)
        try:
            # Truyền tham số đặc biệt cho completeness
            if stage_name == 'completeness':
                stage_result = func(
                    df,
                    warning_threshold=warning_threshold,
                    error_threshold=error_threshold,
                    field_error_thresholds=field_error_thresholds
                )
            else:
                stage_result = func(df)

            results[stage_name] = stage_result

            # Kiểm tra xem stage có lỗi không
            for check_name, check_data in stage_result.items():
                if check_data.get('status') == 'ERROR':
                    has_error = True
                    if not silent:
                        typer.secho(f"  ❌ {check_name}: ERROR", fg=typer.colors.RED)
                elif check_data.get('status') == 'WARNING':
                    if not silent:
                        typer.secho(f"  ⚠️ {check_name}: WARNING", fg=typer.colors.YELLOW)
            if not silent:
                typer.secho(f"✅ Stage {stage_name} hoàn tất.", fg=typer.colors.GREEN)
        except Exception as e:
            typer.secho(f"❌ Lỗi khi chạy stage {stage_name}: {e}", fg=typer.colors.RED, err=True)
            has_error = True
            # Vẫn tiếp tục các stage khác

    # 7. Tạo metadata cho báo cáo
    metadata = {
        'timestamp': datetime.now().isoformat(),
        'total_records': len(df),
        'stages_run': stages_to_run,
        'silver_file': str(silver_file)
    }

    # 8. Xuất báo cáo
    if output_dir is None:
        output_dir = Path(config.get('report_dir', 'data/quality'))
    if not silent:
        print_console(results, metadata)
    report_formats = config.get('report_formats', ['md', 'json'])
    save_report(results, output_dir, metadata, formats=report_formats)

    # 9. Trả về exit code
    return 1 if has_error else 0


def main():
    """Entry point khi chạy trực tiếp runner.py."""
    import argparse
    parser = argparse.ArgumentParser(description="Run Data Quality checks")
    parser.add_argument("--silver-file", type=Path, default=Path("data/silver/jobs_silver.parquet"),
                        help="Path to Silver Parquet file")
    parser.add_argument("--output-dir", type=Path, default=Path("data/quality"),
                        help="Directory to save reports")
    parser.add_argument("--stages", type=str, help="Comma-separated list of stages to run (e.g., completeness,validity)")
    parser.add_argument("--silent", action="store_true", help="Suppress console output")
    args = parser.parse_args()

    stages_list = args.stages.split(',') if args.stages else None
    exit_code = run_quality(
        silver_file=args.silver_file,
        output_dir=args.output_dir,
        stages=stages_list,
        silent=args.silent
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()