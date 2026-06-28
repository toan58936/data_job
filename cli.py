#!/usr/bin/env python
"""
CLI tool cho hệ thống tuyển dụng ngành Data.
Điều phối các tác vụ: crawl (list, detail, text), transform, và pipeline toàn bộ.
Hỗ trợ đa nguồn: TopCV, ITviec.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        os.system("chcp 65001 > nul 2>&1")
    except Exception:
        pass

import typer
import yaml

app = typer.Typer(
    name="data-pipeline",
    help="CLI cho hệ thống thu thập và xử lý dữ liệu tuyển dụng ngành Data",
    add_completion=True,
)

PROJECT_ROOT = Path(__file__).parent
CRAWLER_DIR = PROJECT_ROOT / "crawlers"
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"
LOGS_DIR = PROJECT_ROOT / "logs"

SUPPORTED_SOURCES = ["topcv", "itviec"]


# ==================== HELPER FUNCTIONS ====================

def run_command(cmd: list, cwd: Optional[Path] = None, env: Optional[dict] = None) -> int:
    """Chạy lệnh và in output trực tiếp, trả về exit code."""
    full_env = {**os.environ, **(env or {})}
    typer.echo(f"Running: {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=full_env)
    return result.returncode


def load_roles_from_config(config_path: Optional[Path] = None) -> list:
    """Đọc danh sách role từ config.yaml. Fallback nếu không có."""
    if config_path is None:
        config_path = PROJECT_ROOT / "config.yaml"
    default_roles = [
        'data-engineer',
        'data-analyst',
        'data-scientist',
        'business-intelligence'
    ]
    if not config_path.exists():
        return default_roles
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        roles = config.get('crawler', {}).get('roles')
        if isinstance(roles, list) and roles:
            return roles
    except Exception:
        pass
    return default_roles


def resolve_crawler_script(source: str, task: str) -> Optional[Path]:
    """Trả về đường dẫn script crawler phù hợp theo source và task."""
    if source == "topcv":
        if task == "list":
            return CRAWLER_DIR / "src" / "topcv" / "list_crawler.js"
        elif task == "detail":
            return CRAWLER_DIR / "src" / "topcv" / "detail_crawler.js"
        elif task == "text":
            return CRAWLER_DIR / "src" / "topcv" / "text_crawler.js"
    elif source == "itviec":
        if task == "list":
            return CRAWLER_DIR / "src" / "itviec" / "list_crawler.js"
        elif task == "detail":
            return CRAWLER_DIR / "src" / "itviec" / "detail_crawler.js"
        elif task == "text":
            typer.secho("⚠️ ITviec không hỗ trợ crawler text.", fg=typer.colors.YELLOW)
            return None
    return None


# ==================== COMMANDS ====================

@app.command()
def version():
    """Hiển thị phiên bản CLI."""
    from importlib.metadata import version as pkg_version
    try:
        ver = pkg_version("topcv-data-engineer")
    except Exception:
        ver = "0.1.0"
    typer.echo(f"data-pipeline CLI v{ver}")


@app.command()
def status(
    source: Optional[str] = typer.Option(
        None, "--source", help="Lọc theo nguồn: topcv, itviec, hoặc all"
    ),
):
    """Hiển thị trạng thái dữ liệu hiện tại."""
    sources = [source] if source else SUPPORTED_SOURCES
    typer.secho("===== TRẠNG THÁI HỆ THỐNG =====", fg=typer.colors.CYAN)

    for src in sources:
        if src not in SUPPORTED_SOURCES:
            typer.secho(f"  ❌ Nguồn '{src}' không hợp lệ. Chọn: {', '.join(SUPPORTED_SOURCES)}", fg=typer.colors.RED)
            continue

        src_dir = BRONZE_DIR / src
        typer.secho(f"\n📁 Nguồn: {src.upper()}", fg=typer.colors.MAGENTA)

        for fname in ["jobs_all.json", "jobs_detail.json", "job_text_final.json"]:
            full_path = src_dir / fname
            if full_path.exists():
                size = full_path.stat().st_size
                typer.echo(f"  ✅ {fname} ({size:,} bytes)")
            else:
                typer.echo(f"  ❌ {fname} (không tìm thấy)")

        all_file = src_dir / "jobs_all.json"
        if all_file.exists():
            try:
                with open(all_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                typer.echo(f"  Số job trong jobs_all.json: {len(data)}")
            except Exception:
                pass

    silver_file = SILVER_DIR / "jobs_silver.parquet"
    if silver_file.exists():
        size = silver_file.stat().st_size
        typer.echo(f"\n✅ Silver Parquet ({size:,} bytes)")
        try:
            import pandas as pd
            df = pd.read_parquet(silver_file)
            typer.echo(f"   Số dòng: {len(df)}")
            if 'source' in df.columns:
                typer.echo(f"   Phân bổ nguồn:\n{df['source'].value_counts().to_string()}")
        except ImportError:
            pass
    else:
        typer.echo("\n❌ Silver Parquet chưa được tạo")

    typer.echo(f"\nĐường dẫn làm việc:")
    typer.echo(f"  PROJECT_ROOT: {PROJECT_ROOT}")


@app.command()
def crawl(
    task: str = typer.Argument(
        "all", help="Tác vụ crawl: list, detail, text, hoặc all (mặc định)"
    ),
    source: str = typer.Option(
        "topcv", "--source", help="Nguồn dữ liệu: topcv, itviec, hoặc all"
    ),
    headless: bool = typer.Option(True, "--headless/--headed", help="Chạy headless hay hiện browser"),
    roles: str = typer.Option("all", "--roles", help="Danh sách role: 'all' hoặc 'role1,role2'"),
    config: Optional[Path] = typer.Option(None, "--config", help="Đường dẫn config.yaml"),
):
    """Chạy crawler để thu thập dữ liệu từ TopCV và/hoặc ITviec."""
    if source == "all":
        crawl_sources = ["topcv", "itviec"]
    elif source in SUPPORTED_SOURCES:
        crawl_sources = [source]
    else:
        typer.secho(f"Nguồn '{source}' không hợp lệ. Chọn: {', '.join(SUPPORTED_SOURCES)} hoặc 'all'", fg=typer.colors.RED)
        raise typer.Exit(1)

    if task not in ["list", "detail", "text", "all"]:
        typer.secho(f"Tác vụ '{task}' không hợp lệ. Chọn: list, detail, text, all", fg=typer.colors.RED)
        raise typer.Exit(1)

    for src in crawl_sources:
        typer.secho(f"\n{'='*50}", fg=typer.colors.CYAN)
        typer.secho(f"📡 Crawling nguồn: {src.upper()}", fg=typer.colors.CYAN)
        typer.secho(f"{'='*50}", fg=typer.colors.CYAN)

        tasks_to_run = ["list", "detail", "text"] if task == "all" else [task]

        for t in tasks_to_run:
            if t == "text" and src == "itviec":
                typer.secho("⏭️  Bỏ qua task 'text' cho ITviec (không hỗ trợ).", fg=typer.colors.YELLOW)
                continue

            script_path = resolve_crawler_script(src, t)
            if script_path is None:
                typer.secho(f"❌ Không tìm thấy script crawler cho {src} - {t}", fg=typer.colors.RED)
                continue

            if not script_path.exists():
                typer.secho(f"❌ File {script_path} không tồn tại!", fg=typer.colors.RED)
                continue

            typer.echo(f"\n🔍 [{src}] Tác vụ: {t}")

            if t == "list":
                role_list = load_roles_from_config(config)
                if roles != "all":
                    role_list = [r.strip() for r in roles.split(',') if r.strip()]
                if not role_list:
                    typer.secho("❌ Không có role nào để crawl!", fg=typer.colors.RED)
                    raise typer.Exit(1)

                cmd = ["uv", "run", "node", str(script_path), "--roles", ",".join(role_list)]
                env = {"HEADLESS": "true" if headless else "false"}
                result = run_command(cmd, cwd=CRAWLER_DIR, env=env)
            else:
                cmd = ["uv", "run", "node", str(script_path)]
                env = {"HEADLESS": "true" if headless else "false"}
                result = run_command(cmd, cwd=CRAWLER_DIR, env=env)

            if result != 0:
                typer.secho(f"❌ Crawler {src} - {t} thất bại với mã lỗi {result}!", fg=typer.colors.RED)
                raise typer.Exit(result)

            typer.secho(f"✅ Crawler {src} - {t} hoàn tất.", fg=typer.colors.GREEN)

    typer.secho("\n✅ Hoàn tất tất cả các tác vụ crawl.", fg=typer.colors.GREEN)


@app.command()
def transform(
    format: str = typer.Option("parquet", "--format", help="Định dạng output: parquet hoặc csv"),
    no_gold: bool = typer.Option(False, "--no-gold", help="Không xây dựng Gold layer"),
    no_quality: bool = typer.Option(False, "--no-quality", help="Không chạy Data Quality"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", help="Thư mục output Silver"),
    config: Optional[Path] = typer.Option(None, "--config", help="Đường dẫn config.yaml"),
):
    """Chạy transform để chuẩn hóa dữ liệu từ Bronze lên Silver."""
    from transform.src.orchestrator.pipeline import run_pipeline
    from transform.src.utils.config_loader import load_config as _load_config

    typer.secho("Bắt đầu transform...", fg=typer.colors.YELLOW)

    cfg = _load_config(config) if config else _load_config()
    bronze_dir = PROJECT_ROOT / cfg.get('pipeline', {}).get('bronze_dir', 'data/bronze')

    if output_dir is None:
        output_dir = PROJECT_ROOT / cfg.get('pipeline', {}).get('silver_dir', 'data/silver')

    silver_file = output_dir / f"jobs_silver.{format}"

    exit_code = run_pipeline(
        bronze_dir=bronze_dir,
        silver_file=silver_file,
        output_format=format,
        run_quality_checks=not no_quality,
        run_gold=not no_gold
    )
    if exit_code != 0:
        typer.secho(f"Transform thất bại với mã lỗi {exit_code}!", fg=typer.colors.RED)
        raise typer.Exit(exit_code)
    typer.secho("Transform hoàn tất.", fg=typer.colors.GREEN)


@app.command()
def run(
    headless: bool = typer.Option(True, "--headless/--headed", help="Chế độ headless cho crawler"),
    format: str = typer.Option("parquet", "--format", help="Định dạng output cho transform"),
    no_gold: bool = typer.Option(False, "--no-gold", help="Không xây dựng Gold layer"),
    no_quality: bool = typer.Option(False, "--no-quality", help="Không chạy Data Quality"),
    source: str = typer.Option("all", "--source", help="Nguồn dữ liệu: topcv, itviec, hoặc all"),
    roles: str = typer.Option("all", "--roles", help="Danh sách role: 'all' hoặc 'role1,role2'"),
):
    """
    Chạy toàn bộ pipeline: crawl + transform.
    Mặc định crawl tất cả nguồn (topcv + itviec).
    """
    typer.secho("===== BẮT ĐẦU PIPELINE =====", fg=typer.colors.CYAN)

    # 1. Crawl
    typer.secho("\n[1/2] Đang chạy crawler...", fg=typer.colors.YELLOW)
    cmd_crawl = [sys.executable, str(PROJECT_ROOT / "cli.py"), "crawl", "all"]
    if not headless:
        cmd_crawl.append("--headed")
    if source:
        cmd_crawl.extend(["--source", source])
    if roles:
        cmd_crawl.extend(["--roles", roles])
    result = subprocess.run(cmd_crawl, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        typer.secho("❌ Crawler thất bại!", fg=typer.colors.RED)
        raise typer.Exit(result.returncode)

    # 2. Transform
    typer.secho("\n[2/2] Đang chạy transform...", fg=typer.colors.YELLOW)
    cmd_transform = [sys.executable, str(PROJECT_ROOT / "cli.py"), "transform", "--format", format]
    if no_gold:
        cmd_transform.append("--no-gold")
    if no_quality:
        cmd_transform.append("--no-quality")
    result = subprocess.run(cmd_transform, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        typer.secho("❌ Transform thất bại!", fg=typer.colors.RED)
        raise typer.Exit(result.returncode)

    typer.secho("\n✅ Pipeline hoàn tất!", fg=typer.colors.GREEN)


@app.command()
def gold(
    silver_file: Optional[Path] = typer.Option(None, "--silver-file", help="Đường dẫn đến file Silver Parquet"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", help="Thư mục lưu Gold"),
):
    """Xây dựng Gold Layer từ Silver."""
    from transform.src.gold.gold_builder import build_gold

    if silver_file is None:
        silver_file = SILVER_DIR / "jobs_silver.parquet"
    if output_dir is None:
        output_dir = PROJECT_ROOT / "data" / "gold"

    if not silver_file.exists():
        typer.secho(f"❌ File Silver không tồn tại: {silver_file}", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"📦 Building Gold from {silver_file} to {output_dir}...", fg=typer.colors.CYAN)
    exit_code = build_gold(silver_file, output_dir)
    if exit_code != 0:
        typer.secho("❌ Gold build failed!", fg=typer.colors.RED)
        raise typer.Exit(exit_code)
    typer.secho("✅ Gold build completed!", fg=typer.colors.GREEN)


@app.command()
def quality(
    silver_file: Optional[Path] = typer.Option(None, "--silver-file"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir"),
    stages: Optional[str] = typer.Option(None, "--stages"),
    silent: bool = typer.Option(False, "--silent"),
    config_file: Optional[Path] = typer.Option(None, "--config", help="Path to config.yaml"),
):
    """Chạy Data Quality checks trên Silver data."""
    from transform.src.quality.runner import run_quality
    from transform.src.utils.config_loader import load_config

    config = load_config(config_file) if config_file else load_config()
    quality_cfg = config.get('quality', {})

    if silver_file is None:
        silver_file = PROJECT_ROOT / quality_cfg.get('silver_file', 'data/silver/jobs_silver.parquet')
    if output_dir is None:
        output_dir = PROJECT_ROOT / quality_cfg.get('report_dir', 'data/quality')
    stage_list = stages.split(",") if stages else quality_cfg.get('enabled_stages')

    typer.secho(f"🔍 Running quality checks on {silver_file}...", fg=typer.colors.CYAN)
    exit_code = run_quality(
        silver_file=silver_file,
        output_dir=output_dir,
        stages=stage_list,
        silent=silent,
        config=quality_cfg
    )
    if exit_code == 0:
        typer.secho("✅ Quality checks passed!", fg=typer.colors.GREEN)
    else:
        typer.secho(f"⚠️ Quality checks completed with issues (exit code: {exit_code})", fg=typer.colors.YELLOW)
    raise typer.Exit(exit_code)


@app.command()
def test(
    path: str = typer.Option("transform/tests", "--path", help="Đường dẫn thư mục hoặc file test"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Chi tiết output"),
):
    """Chạy pytest."""
    cmd = ["uv", "run", "pytest", path]
    if verbose:
        cmd.append("-v")
    exit_code = run_command(cmd, cwd=PROJECT_ROOT)
    if exit_code != 0:
        typer.secho("❌ Test thất bại!", fg=typer.colors.RED)
        raise typer.Exit(exit_code)
    typer.secho("✅ Test hoàn tất.", fg=typer.colors.GREEN)


@app.command()
def dashboard(
    port: int = typer.Option(8501, "--port", help="Port chạy Streamlit"),
    no_rerun: bool = typer.Option(False, "--no-rerun", help="Tắt auto-reload"),
):
    """Mở Streamlit dashboard."""
    cmd = ["uv", "run", "streamlit", "run", "dashboard/app.py", "--server.port", str(port)]
    if no_rerun:
        cmd.extend(["--server.runOnSave", "false"])
    typer.secho(f"🚀 Mở dashboard tại http://localhost:{port}", fg=typer.colors.CYAN)
    run_command(cmd, cwd=PROJECT_ROOT)


@app.command()
def clean(
    source: Optional[str] = typer.Option(
        None, "--source", help="Chỉ clean nguồn cụ thể: topcv, itviec, hoặc all"
    ),
):
    """Xóa các file tạm (checkpoint, logs) và output cũ."""
    sources = [source] if source else SUPPORTED_SOURCES
    typer.secho("Cleaning...", fg=typer.colors.YELLOW)

    for src in sources:
        if src not in SUPPORTED_SOURCES:
            continue
        src_dir = BRONZE_DIR / src
        for f in src_dir.glob("checkpoint*.json"):
            typer.echo(f"  Removing {f}")
            f.unlink()
        for f in src_dir.glob("*.log"):
            typer.echo(f"  Removing {f}")
            f.unlink()

    silver_file = SILVER_DIR / "jobs_silver.parquet"
    if silver_file.exists():
        typer.echo(f"  Removing {silver_file}")
        silver_file.unlink()
    silver_csv = SILVER_DIR / "jobs_silver.csv"
    if silver_csv.exists():
        typer.echo(f"  Removing {silver_csv}")
        silver_csv.unlink()

    typer.secho("Clean completed.", fg=typer.colors.GREEN)


@app.command()
def shell():
    """Mở một shell với môi trường uv."""
    typer.echo("Mở shell với uv...")
    subprocess.run(["uv", "run", "bash"], cwd=PROJECT_ROOT)


@app.command()
def sources():
    """Hiển thị danh sách nguồn dữ liệu hiện có."""
    typer.secho("===== NGUỒN DỮ LIỆU =====", fg=typer.colors.CYAN)
    for src in SUPPORTED_SOURCES:
        src_dir = BRONZE_DIR / src
        exists = "✅ Có sẵn" if src_dir.exists() else "❌ Chưa có"
        typer.echo(f"  {src}: {exists}")
        if src_dir.exists():
            for f in sorted(src_dir.glob("jobs_*.json")):
                size = f.stat().st_size
                typer.echo(f"    - {f.name} ({size:,} bytes)")


if __name__ == "__main__":
    app()