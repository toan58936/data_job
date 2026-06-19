#!/usr/bin/env python
"""
CLI tool cho hệ thống tuyển dụng ngành Data.
Điều phối các tác vụ: crawl (list, detail, text), transform, và pipeline toàn bộ.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(
    name="data-pipeline",
    help="CLI cho hệ thống thu thập và xử lý dữ liệu tuyển dụng ngành Data",
    add_completion=True,
)

# Đường dẫn thư mục dự án
PROJECT_ROOT = Path(__file__).parent
CRAWLER_DIR = PROJECT_ROOT / "crawlers"
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"
LOGS_DIR = PROJECT_ROOT / "logs"

# File bronze
BRONZE_FILES = {
    "all": BRONZE_DIR / "jobs_all.json",
    "detail": BRONZE_DIR / "jobs_detail.json",
    "text": BRONZE_DIR / "job_text_final.json",
}


def run_command(cmd: list, cwd: Optional[Path] = None, env: Optional[dict] = None) -> int:
    """Chạy lệnh và in output trực tiếp, trả về exit code."""
    full_env = {**os.environ, **(env or {})}
    typer.echo(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=full_env)
    return result.returncode


@app.command()
def status():
    """
    Hiển thị trạng thái của dữ liệu hiện tại.
    """
    typer.secho("===== TRẠNG THÁI HỆ THỐNG =====", fg=typer.colors.CYAN)

    # Kiểm tra các file Bronze
    typer.echo("Dữ liệu Bronze:")
    for name, path in BRONZE_FILES.items():
        if path.exists():
            size = path.stat().st_size
            typer.echo(f"  ✅ {path.name} ({size} bytes)")
        else:
            typer.echo(f"  ❌ {path.name} (không tìm thấy)")

    # Đếm số job trong jobs_all.json nếu có
    if BRONZE_FILES["all"].exists():
        try:
            with open(BRONZE_FILES["all"], "r", encoding="utf-8") as f:
                data = json.load(f)
            typer.echo(f"  Số job trong jobs_all.json: {len(data)}")
        except:
            pass

    # Kiểm tra file Silver
    silver_file = SILVER_DIR / "jobs_silver.parquet"
    if silver_file.exists():
        size = silver_file.stat().st_size
        typer.echo(f"\n✅ Silver Parquet ({size} bytes)")
        try:
            import pandas as pd
            df = pd.read_parquet(silver_file)
            typer.echo(f"   Số dòng: {len(df)}")
        except ImportError:
            pass
    else:
        typer.echo("\n❌ Silver Parquet chưa được tạo")

    # Đường dẫn làm việc
    typer.echo(f"\nĐường dẫn làm việc:")
    typer.echo(f"  PROJECT_ROOT: {PROJECT_ROOT}")


@app.command()
def crawl(
    task: str = typer.Argument(
        "all", help="Tác vụ crawl: list, detail, text, hoặc all (mặc định)"
    ),
    headless: bool = typer.Option(True, "--headless/--headed", help="Chạy headless hay hiện browser"),
):
    """
    Chạy crawler để thu thập dữ liệu từ TopCV.
    """
    if task not in ["list", "detail", "text", "all"]:
        typer.secho(f"Tác vụ '{task}' không hợp lệ. Chọn: list, detail, text, all", fg=typer.colors.RED)
        raise typer.Exit(1)

    script_map = {
        "list": "topcv-list-crawler.js",
        "detail": "topcv-detail-crawler.js",
        "text": "topcv-text-crawler.js",
    }

    if task == "all":
        tasks = ["list", "detail", "text"]
    else:
        tasks = [task]

    for t in tasks:
        script = script_map[t]
        script_path = CRAWLER_DIR / "src" / script
        if not script_path.exists():
            typer.secho(f"File {script_path} không tồn tại!", fg=typer.colors.RED)
            raise typer.Exit(1)

        cmd = ["uv", "run", "node", str(script_path)]
        env = {"HEADLESS": "true" if headless else "false"}
        typer.echo(f"Chạy crawler {t}...")
        result = run_command(cmd, cwd=CRAWLER_DIR, env=env)
        if result != 0:
            typer.secho(f"Crawler {t} thất bại với mã lỗi {result}!", fg=typer.colors.RED)
            raise typer.Exit(result)
        typer.secho(f"Crawler {t} hoàn tất.", fg=typer.colors.GREEN)

    typer.secho("Hoàn tất tất cả các tác vụ crawl.", fg=typer.colors.GREEN)


@app.command()
def transform(
    format: str = typer.Option("parquet", "--format", help="Định dạng output: parquet hoặc csv"),
):
    """
    Chạy transform để chuẩn hóa dữ liệu từ Bronze lên Silver.
    """
    typer.echo("Bắt đầu transform...")
    cmd = ["uv", "run", "python", "-m", "transform.src.main"]
    result = run_command(cmd, cwd=PROJECT_ROOT)
    if result != 0:
        typer.secho(f"Transform thất bại với mã lỗi {result}!", fg=typer.colors.RED)
        raise typer.Exit(result)
    typer.secho("Transform hoàn tất.", fg=typer.colors.GREEN)


@app.command()
def run(
    headless: bool = typer.Option(True, "--headless/--headed", help="Chế độ headless cho crawler"),
):
    """
    Chạy toàn bộ pipeline: crawl all + transform.
    Sử dụng script run_pipeline.ps1 để thực thi.
    """
    typer.secho("===== BẮT ĐẦU PIPELINE =====", fg=typer.colors.CYAN)
    script_path = PROJECT_ROOT / "run_pipeline.ps1"
    if not script_path.exists():
        typer.secho("❌ Không tìm thấy script run_pipeline.ps1", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Nếu user chọn --headed, script hiện không hỗ trợ, nhưng có thể thông báo
    if not headless:
        typer.secho("⚠️ Script run_pipeline.ps1 hiện chỉ hỗ trợ headless mode. Bỏ qua --headed.", fg=typer.colors.YELLOW)

    # Chạy script PowerShell
    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        typer.secho("❌ Pipeline thất bại!", fg=typer.colors.RED)
        raise typer.Exit(result.returncode)
    typer.secho("✅ Pipeline hoàn tất!", fg=typer.colors.GREEN)


@app.command()
def clean():
    """
    Xóa các file tạm (checkpoint, logs) và output cũ (nếu có).
    """
    typer.secho("Cleaning...", fg=typer.colors.YELLOW)

    for f in BRONZE_DIR.glob("checkpoint*.json"):
        typer.echo(f"  Removing {f}")
        f.unlink()

    silver_file = SILVER_DIR / "jobs_silver.parquet"
    if silver_file.exists():
        typer.echo(f"  Removing {silver_file}")
        silver_file.unlink()

    typer.secho("Clean completed.", fg=typer.colors.GREEN)


@app.command()
def quality(
    silver_file: Optional[Path] = typer.Option(None, "--silver-file"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir"),
    stages: Optional[str] = typer.Option(None, "--stages"),
    silent: bool = typer.Option(False, "--silent"),
    config_file: Optional[Path] = typer.Option(None, "--config", help="Path to config.yaml"),
):
    from transform.src.quality.runner import run_quality
    from transform.src.utils.config_loader import load_config

    config = load_config(config_file) if config_file else load_config()
    quality_cfg = config.get('quality', {})

    if silver_file is None:
        silver_file = PROJECT_ROOT / quality_cfg.get('silver_file', 'data/silver/jobs_silver.parquet')
    if output_dir is None:
        output_dir = PROJECT_ROOT / quality_cfg.get('report_dir', 'data/quality')
    stage_list = stages.split(",") if stages else quality_cfg.get('enabled_stages')

    exit_code = run_quality(
        silver_file=silver_file,
        output_dir=output_dir,
        stages=stage_list,
        silent=silent,
        config=quality_cfg
    )
    raise typer.Exit(exit_code)


@app.command()
def shell():
    """
    Mở một shell với môi trường uv.
    """
    typer.echo("Mở shell với uv...")
    subprocess.run(["uv", "run", "bash"], cwd=PROJECT_ROOT)


if __name__ == "__main__":
    app()