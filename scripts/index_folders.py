"""Подписи папок: _index.md в каждом верхнем разделе + README корня.

  uv run scripts/index_folders.py
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from common import CORPUS_DEFAULT

PURPOSE = {
    "00-Каталог": "Каталог файлов, дубли, карта переносов, оценка базы, регламент.",
    "01-Нормы": "Полные тексты ТНПА РБ: СН, СП, СТБ, ГОСТ, ТКП, СНБ и пакеты постановлений.",
    "02-Сортаменты": "ГОСТы на прокат, трубы, крепёж, сварку; реестр сортаментов.",
    "03-Серии": "Типовые серии конструкций и изделий по разделам.",
    "04-Аудиты": "Разобранные объекты, чек-листы, промпты аудиторов, журнал оценок.",
    "05-BIM": "BIM-шаблоны, IDS-проверки, классификаторы, пилот IFC, сортаменты CSV.",
    "06-Справочники": "Справочник, чек-листы, индексы, карта металла/ЖБ, карточки изделий, оформление.",
    "07-Акты": "Законы, постановления, приказы, технические регламенты.",
    "08-Обучение": "Программа обучения и конспекты.",
    "09-Инструменты": "Обзор ПО для проектирования (AutoCAD, Revit).",
    "_архив": "Старые папки, дубли и отменённые подборки. Не для работы.",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(CORPUS_DEFAULT))
    args = ap.parse_args()
    corpus = Path(args.corpus)

    tops = [p for p in sorted(corpus.iterdir()) if p.is_dir() and (p.name[:2].isdigit() or p.name.startswith("_"))]
    lines = ["# Карта корпуса", ""]
    for d in tops:
        files = [f for f in d.rglob("*") if f.is_file()]
        exts = Counter(f.suffix.lower() for f in files)
        subdirs = [s.name for s in sorted(d.iterdir()) if s.is_dir()][:12]
        purpose = PURPOSE.get(d.name, "Служебная папка.")
        lines.append(f"## {d.name}")
        lines.append(purpose)
        lines.append("")
        lines.append(f"Файлов: {len(files)}; форматы: " + ", ".join(f"{k or '—'}={v}" for k, v in exts.most_common(6)))
        if subdirs:
            lines.append("Подпапки: " + ", ".join(subdirs))
        lines.append("")

        idx = [f"# {d.name}", "", purpose, "", f"Файлов: {len(files)}."]
        if subdirs:
            idx += ["", "## Подпапки", ""] + [f"- `{s}`" for s in subdirs]
        idx += ["", "## Содержимое (первые 40)", ""]
        for f in sorted(files)[:40]:
            idx.append(f"- `{f.relative_to(d).as_posix()}`")
        if len(files) > 40:
            idx.append(f"- … ещё {len(files) - 40}")
        idx += ["", "Полный перечень — `00-Каталог/catalog-all.csv`."]
        (d / "_index.md").write_text("\n".join(idx) + "\n", encoding="utf-8")

    lines += ["## Корень", "", "- `02-Реестр.csv` — реестр ТНПА (источник истины по статусам);",
              "- `README.md` — эта карта;", "- `00-Каталог/РЕГЛАМЕНТ.md` — правила имён и раскладки."]
    (corpus / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("folders:", len(tops))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
