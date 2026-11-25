import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "check-assets.py"


def run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), "--root", str(root)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def make_page(root: Path, html: str) -> None:
    page = root / "app" / "ui" / "index.html"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(html, encoding="utf-8")


def test_missing_asset_fails(tmp_path):
    make_page(tmp_path, '<link rel="stylesheet" href="assets/missing.css">')
    result = run(tmp_path)
    assert result.returncode == 1
    assert "MISSING" in result.stdout


def test_existing_asset_passes(tmp_path):
    asset = tmp_path / "app" / "ui" / "assets" / "a.css"
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_text("body{}", encoding="utf-8")
    make_page(tmp_path, '<link rel="stylesheet" href="assets/a.css">')
    brand = tmp_path / "app" / "ui" / "brand" / "index.html"
    brand.parent.mkdir(parents=True, exist_ok=True)
    brand.write_text('<img src="../assets/a.css">', encoding="utf-8")
    result = run(tmp_path)
    assert result.returncode == 0, result.stdout
    assert "0 missing" in result.stdout


def test_external_anchor_and_route_skipped(tmp_path):
    make_page(
        tmp_path,
        '<a href="https://example.com/x">x</a>'
        '<a href="#top">top</a>'
        '<a href="/app">app</a>'
        '<img src="data:image/png;base64,AA==">',
    )
    result = run(tmp_path)
    assert result.returncode == 0, result.stdout
