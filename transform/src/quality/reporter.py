"""
reporter.py - Tạo báo cáo từ kết quả kiểm tra chất lượng dữ liệu.
Hỗ trợ các định dạng: console (màu), Markdown, JSON.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

import typer


def generate_markdown(results: Dict[str, Any], metadata: Dict[str, Any]) -> str:
    """
    Tạo báo cáo dạng Markdown từ kết quả các stage.

    Args:
        results: Dict chứa kết quả của từng stage (key = stage name).
        metadata: Dict chứa thông tin bổ sung (timestamp, total_records, stages_run).

    Returns:
        str: Nội dung báo cáo Markdown.
    """
    lines = []
    lines.append("# Báo cáo chất lượng dữ liệu\n")
    lines.append(f"- **Thời gian**: {metadata.get('timestamp', datetime.now().isoformat())}")
    lines.append(f"- **Tổng số records**: {metadata.get('total_records', 0)}")
    lines.append(f"- **Các stage đã chạy**: {', '.join(metadata.get('stages_run', []))}\n")

    # Tóm tắt tổng thể
    lines.append("## Tóm tắt tổng thể\n")
    lines.append("| Giai đoạn | Số check | OK | WARNING | ERROR |")
    lines.append("|-----------|----------|----|---------|-------|")
    for stage_name, stage_data in results.items():
        total = len(stage_data)
        ok_count = sum(1 for v in stage_data.values() if v.get('status') == 'OK')
        warning_count = sum(1 for v in stage_data.values() if v.get('status') == 'WARNING')
        error_count = sum(1 for v in stage_data.values() if v.get('status') == 'ERROR')
        lines.append(f"| {stage_name} | {total} | {ok_count} | {warning_count} | {error_count} |")
    lines.append("")

    # Chi tiết từng stage
    for stage_name, stage_data in results.items():
        lines.append(f"## {stage_name.capitalize()}\n")
        for check_name, check_result in stage_data.items():
            status = check_result.get('status', 'UNKNOWN')
            icon = "✅" if status == 'OK' else "⚠️" if status == 'WARNING' else "❌"
            lines.append(f"### {check_name} {icon}")
            lines.append(f"- **Trạng thái**: {status}")
            if 'violations' in check_result:
                lines.append(f"- **Số vi phạm**: {check_result['violations']}")
            if 'percentage' in check_result:
                lines.append(f"- **Tỷ lệ**: {check_result['percentage']:.2f}%")
            if 'count' in check_result and 'total' in check_result:
                lines.append(f"- **Có dữ liệu**: {check_result['count']}/{check_result['total']}")

            # Hiển thị chi tiết vi phạm (nếu có)
            details = check_result.get('details', [])
            if details:
                lines.append("- **Chi tiết vi phạm**:")
                # Giới hạn hiển thị 10 dòng đầu
                for i, item in enumerate(details[:10]):
                    lines.append(f"  - {json.dumps(item, ensure_ascii=False)}")
                if len(details) > 10:
                    lines.append(f"  - ... và {len(details) - 10} dòng khác")
            lines.append("")

    return "\n".join(lines)


def generate_json(results: Dict[str, Any], metadata: Dict[str, Any]) -> str:
    """
    Tạo báo cáo dạng JSON.

    Args:
        results: Dict chứa kết quả của từng stage.
        metadata: Dict chứa thông tin bổ sung.

    Returns:
        str: Chuỗi JSON.
    """
    output = {
        "metadata": metadata,
        "results": results
    }
    return json.dumps(output, indent=2, ensure_ascii=False)


def print_console(results: Dict[str, Any], metadata: Dict[str, Any]) -> None:
    """
    In báo cáo ra console với màu sắc (dùng typer).

    Args:
        results: Dict chứa kết quả của từng stage.
        metadata: Dict chứa thông tin bổ sung.
    """
    typer.secho("===== BÁO CÁO CHẤT LƯỢNG DỮ LIỆU =====", fg=typer.colors.CYAN, bold=True)
    typer.echo(f"Thời gian: {metadata.get('timestamp', datetime.now().isoformat())}")
    typer.echo(f"Tổng số records: {metadata.get('total_records', 0)}")
    typer.echo(f"Các stage đã chạy: {', '.join(metadata.get('stages_run', []))}\n")

    # Tóm tắt tổng thể
    typer.secho("TÓM TẮT TỔNG THỂ", fg=typer.colors.CYAN, bold=True)
    for stage_name, stage_data in results.items():
        total = len(stage_data)
        ok_count = sum(1 for v in stage_data.values() if v.get('status') == 'OK')
        warning_count = sum(1 for v in stage_data.values() if v.get('status') == 'WARNING')
        error_count = sum(1 for v in stage_data.values() if v.get('status') == 'ERROR')
        color = typer.colors.GREEN if error_count == 0 else typer.colors.RED
        typer.secho(
            f"  {stage_name}: {total} checks, OK={ok_count}, WARNING={warning_count}, ERROR={error_count}",
            fg=color
        )
    typer.echo("")

    # Chi tiết từng stage (chỉ in các check có WARNING/ERROR để tránh dài dòng)
    typer.secho("CHI TIẾT CẢNH BÁO/LỖI", fg=typer.colors.YELLOW, bold=True)
    has_issue = False
    for stage_name, stage_data in results.items():
        for check_name, check_result in stage_data.items():
            status = check_result.get('status', 'UNKNOWN')
            if status in ('WARNING', 'ERROR'):
                has_issue = True
                icon = "⚠️" if status == 'WARNING' else "❌"
                typer.secho(f"  {icon} {stage_name}.{check_name}: {status}", fg=typer.colors.RED if status == 'ERROR' else typer.colors.YELLOW)
                if 'violations' in check_result:
                    typer.echo(f"      Số vi phạm: {check_result['violations']}")
                if 'percentage' in check_result:
                    typer.echo(f"      Tỷ lệ: {check_result['percentage']:.2f}%")
                details = check_result.get('details', [])
                if details:
                    typer.echo("      Chi tiết (tối đa 3):")
                    for i, item in enumerate(details[:3]):
                        typer.echo(f"        - {json.dumps(item, ensure_ascii=False)}")
                    if len(details) > 3:
                        typer.echo(f"        ... và {len(details) - 3} dòng khác")
                typer.echo("")
    if not has_issue:
        typer.secho("  ✅ Không có cảnh báo hoặc lỗi nào!", fg=typer.colors.GREEN)


def save_report(
    results: Dict[str, Any],
    output_dir: Path,
    metadata: Dict[str, Any],
    formats: List[str] = None
) -> None:
    """
    Lưu báo cáo vào thư mục output với các định dạng được chỉ định.
    Báo cáo được lưu theo cấu trúc: output_dir/YYYY-MM-DD/report_timestamp.{md,json}

    Args:
        results: Dict chứa kết quả của từng stage.
        output_dir: Đường dẫn thư mục lưu báo cáo.
        metadata: Dict chứa thông tin bổ sung.
        formats: Danh sách các định dạng cần lưu (mặc định: ['md', 'json']).
    """
    if formats is None:
        formats = ['md', 'json']

    # Tạo thư mục theo ngày
    date_str = datetime.now().strftime("%Y-%m-%d")
    day_dir = output_dir / date_str
    day_dir.mkdir(parents=True, exist_ok=True)

    # Chuẩn hóa timestamp để đặt tên file
    timestamp = metadata.get('timestamp', datetime.now().strftime("%Y%m%d_%H%M%S"))
    if 'T' in timestamp:
        timestamp = timestamp.replace('T', '_').replace(':', '-').split('.')[0]

    if 'md' in formats:
        md_content = generate_markdown(results, metadata)
        md_file = day_dir / f"report_{timestamp}.md"
        md_file.write_text(md_content, encoding='utf-8')
        typer.echo(f"✅ Đã lưu báo cáo Markdown: {md_file}")

    if 'json' in formats:
        json_content = generate_json(results, metadata)
        json_file = day_dir / f"report_{timestamp}.json"
        json_file.write_text(json_content, encoding='utf-8')
        typer.echo(f"✅ Đã lưu báo cáo JSON: {json_file}")