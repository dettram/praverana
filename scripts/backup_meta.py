"""Бэкап метаданных корпуса и скилла (реестр, манифесты, каталог, скрипты).

  uv run scripts/backup_meta.py
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CORPUS_DEFAULT  # noqa: E402

SKILL = Path.home() / ".config" / "opencode" / "skill" / "stroy-calc-audit"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(CORPUS_DEFAULT))
    ap.add_argument("--out-dir", default=str(Path.home() / ".stroy-audit" / "backups"))
    ap.add_argument("--keep", type=int, default=5)
    args = ap.parse_args()

    corpus = Path(args.corpus)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    out = out_dir / f"meta-{stamp}.zip"

    files: list[Path] = []
    files += [corpus / "02-Реестр.csv", corpus / "README.md"]
    files += list((corpus / "00-Каталог").glob("*.csv"))
    files += list((corpus / "00-Каталог").glob("*.md"))
    for man in corpus.glob("_inbox-*/manifest.csv"):
        files.append(man)
    files += list((SKILL / "scripts").glob("*.py"))
    files += list((SKILL / "app").glob("*.py")) if (SKILL / "app").exists() else []
    files += list((SKILL / "app" / "ui").glob("*.html")) if (SKILL / "app" / "ui").exists() else []
    files += list((SKILL / "app").glob("*.md")) if (SKILL / "app").exists() else []
    files += list((SKILL / "references").glob("*.md"))
    files.append(SKILL / "SKILL.md")

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            if f.exists():
                arc = f.relative_to(corpus) if str(f).startswith(str(corpus)) else Path("skill") / f.relative_to(SKILL)
                zf.write(f, arc.as_posix())

    old = sorted(out_dir.glob("meta-*.zip"))
    for f in old[:-args.keep]:
        f.unlink()

    print(f"backup: {out} ({out.stat().st_size / 1024:.0f} KB, files={len(files)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
