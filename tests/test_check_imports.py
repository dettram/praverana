import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "check-imports.py"


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), "--root", str(root)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def test_clean_tree(tmp_path):
    write(tmp_path, "app/a.py", "def a():\n    return 1\n")
    write(tmp_path, "scripts/common.py", "def x():\n    return 1\n")
    write(tmp_path, "scripts/s.py", "from common import x\n")
    result = run(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout


def test_cycle_fails(tmp_path):
    write(tmp_path, "app/a.py", "from b import f\n")
    write(tmp_path, "app/b.py", "from a import g\n")
    result = run(tmp_path)
    assert result.returncode == 1
    assert "FAIL cycle" in result.stdout


def test_scripts_to_app_fails(tmp_path):
    write(tmp_path, "app/c.py", "def c():\n    return 1\n")
    write(tmp_path, "scripts/s.py", "from app import c\n")
    result = run(tmp_path)
    assert result.returncode == 1
    assert "FAIL layer" in result.stdout


def test_app_to_scripts_is_allowed(tmp_path):
    write(tmp_path, "scripts/s.py", "def s():\n    return 1\n")
    write(tmp_path, "app/a.py", "from scripts import s\n")
    result = run(tmp_path)
    assert result.returncode == 0, result.stdout
    assert "OK" in result.stdout


def test_duplicate_module_name_fails(tmp_path):
    write(tmp_path, "app/x.py", "def a():\n    return 1\n")
    write(tmp_path, "scripts/x.py", "def b():\n    return 1\n")
    result = run(tmp_path)
    assert result.returncode == 1
    assert "duplicate module name" in result.stdout
