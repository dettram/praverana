"""История прогонов аудита и сравнение «стало лучше / стало хуже».

Хранилище: ~/.stroy-audit/audit-runs/<время>-<ключ набора>.json.
Ключ набора — имя корневой папки + состав файлов (без размеров), поэтому
правка документа не разрывает историю, а путь и загрузка одной папки совпадают.
Сравнение — по смыслу замечания: (категория, норма, текст без чисел-счётчиков),
а не по номеру строки в таблице.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

HISTORY = Path.home() / ".stroy-audit" / "audit-runs"


def _key(root: str) -> str:
    return hashlib.sha1(str(Path(root)).lower().encode("utf-8")).hexdigest()[:8]


def fingerprint(root: str | Path, names: list[str] | None = None) -> str:
    """Отпечаток состава: относительные имена без размеров.

    Размер не входит: исправление документа не должно разрывать «было/стало».
    """
    if names is None:
        base = Path(root)
        names = [p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()]
    h = hashlib.sha1()
    for name in sorted(str(n).replace("\\", "/") for n in names):
        h.update(name.encode("utf-8") + b"\n")
    return h.hexdigest()[:8]


def dataset_key(root: str | Path, source_name: str | None = None,
                names: list[str] | None = None) -> str:
    """Единый ключ набора: имя корневой папки + отпечаток состава.

    Для загрузки через браузер `source_name` — корневая папка из
    `webkitRelativePath`, а `names` — пути уже без этой папки. Для аудита по
    пути всё считается от самого корня. Одна и та же папка даёт один ключ.
    """
    base = Path(root)
    if names is None:
        names = [p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()]
    source = (source_name or base.name or "project").strip().lower()
    digest = fingerprint(base, names)
    return hashlib.sha1(f"{source}\0{digest}".encode("utf-8")).hexdigest()[:8]


def _files_for(root: str, key: str | None = None) -> list[Path]:
    """Файлы истории по новому ключу и по старому ключу-пути (миграция)."""
    key = key or dataset_key(root)
    files = set(HISTORY.glob(f"*-{key}.json"))
    files.update(HISTORY.glob(f"*-{_key(root)}.json"))
    return sorted(files, reverse=True)


def _norm_text(s: str) -> str:
    s = re.sub(r"\(встречается \d+ раз\)", "", s or "")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def finding_key(f: dict) -> tuple:
    return (f.get("category", ""), f.get("norm", ""), _norm_text(f.get("message", "")))


def save(result: dict, key: str | None = None) -> Path:
    HISTORY.mkdir(parents=True, exist_ok=True)
    root = result["meta"]["root"]
    key = key or result["meta"].get("history_key") or dataset_key(root)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = HISTORY / f"{stamp}-{key}.json"
    serial = 0
    while path.exists():
        serial += 1
        path = HISTORY / f"{stamp}-{key}-{serial}.json"
    path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return path


def previous(root: str, exclude_last: bool = True, key: str | None = None) -> dict | None:
    """Предыдущий прогон для этой папки (последний сохранённый)."""
    HISTORY.mkdir(parents=True, exist_ok=True)
    files = _files_for(root, key)
    if exclude_last and files:
        files = files[1:]
    for f in files:
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
    return None


def list_runs(root: str, limit: int = 6, key: str | None = None) -> list[dict]:
    HISTORY.mkdir(parents=True, exist_ok=True)
    out = []
    for f in _files_for(root, key)[:limit]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        out.append({
            "file": f.name,
            "date": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d.%m.%Y %H:%M"),
            "score": data["summary"]["score"],
            "error": data["summary"]["error"],
            "warn": data["summary"]["warn"],
            "info": data["summary"]["info"],
            "files": data["meta"]["files_scanned"],
            "source": data["meta"].get("source", "path"),
        })
    return out


def compare(old: dict, new: dict) -> dict:
    old_f = {finding_key(f): f for f in old.get("findings", [])}
    new_f = {finding_key(f): f for f in new.get("findings", [])}

    fixed = [old_f[k] for k in old_f if k not in new_f]
    added = [new_f[k] for k in new_f if k not in old_f]

    os_, ns = old["summary"], new["summary"]
    files_old = old["meta"].get("files_scanned", 0)
    files_new = new["meta"].get("files_scanned", 0)
    scope_changed = files_old != files_new
    return {
        "old_date": old["meta"].get("date") or "",
        "old": {"score": os_["score"], "error": os_["error"], "warn": os_["warn"],
                "info": os_["info"]},
        "new": {"score": ns["score"], "error": ns["error"], "warn": ns["warn"],
                "info": ns["info"]},
        "files_old": files_old,
        "files_new": files_new,
        "scope_changed": scope_changed,
        "old_score": os_["score"],
        "new_score": ns["score"],
        "delta": {
            "score": round(ns["score"] - os_["score"], 1),
            "error": ns["error"] - os_["error"],
            "warn": ns["warn"] - os_["warn"],
            "info": ns["info"] - os_["info"],
        },
        "fixed": [{"severity": f["severity"], "category": f["category"],
                   "file": f["file"], "message": f["message"], "norm": f["norm"]}
                  for f in fixed[:40]],
        "added": [{"severity": f["severity"], "category": f["category"],
                   "file": f["file"], "message": f["message"], "norm": f["norm"]}
                  for f in added[:40]],
        "fixed_count": len(fixed),
        "added_count": len(added),
    }
