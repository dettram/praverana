"""Правило №1 из docs/REVIEW.md: циклы импортов и встречные слои.

  uv run python tools/check-imports.py
  uv run python tools/check-imports.py --root <папка>   # проверка самого правила

Сканирует `app/*.py` и `scripts/*.py` и строит граф по именам модулей.
Понимает оба вида импорта: плоский (`from common import ...`) и пакетный
(`from app import engine`, `import app.engine`).
Ищет циклы, самоимпорт и импорт `scripts` -> `app`.
Отложенный импорт (внутри функции) сам по себе не ошибка: он печатается
предупреждением, но цикл, спрятанный в функции, всё равно виден как цикл.
Код возврата 1 — есть нарушение, 0 — чисто.
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

LAYERS = ("app", "scripts")


class Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.depth = 0
        self.items: list[tuple[list[str], bool, int]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.depth += 1
        self.generic_visit(node)
        self.depth -= 1

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.items.append((alias.name.split("."), self.depth > 0, node.lineno))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level or not node.module:
            return
        base = node.module.split(".")
        if base[0] in LAYERS:
            for alias in node.names:
                if alias.name != "*":
                    self.items.append((base + [alias.name], self.depth > 0, node.lineno))
        else:
            self.items.append((base, self.depth > 0, node.lineno))


def parse(path: Path) -> list[tuple[list[str], bool, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    visitor = Visitor()
    visitor.visit(tree)
    return visitor.items


def collect(root: Path) -> tuple[list[Path], dict[Path, list[tuple[Path, int, bool]]], list[str]]:
    files = sorted(p for layer in LAYERS for p in (root / layer).glob("*.py"))
    rel = lambda p: p.relative_to(root).as_posix()  # noqa: E731
    by_stem: dict[str, list[Path]] = {}
    by_layer: dict[tuple[str, str], Path] = {}
    problems: list[str] = []
    for p in files:
        by_stem.setdefault(p.stem, []).append(p)
        by_layer[(p.parent.name, p.stem)] = p
    for stem, paths in by_stem.items():
        if len(paths) > 1:
            problems.append("duplicate module name: " + ", ".join(rel(x) for x in paths))

    edges: dict[Path, list[tuple[Path, int, bool]]] = {p: [] for p in files}
    for p in files:
        try:
            items = parse(p)
        except SyntaxError as exc:
            problems.append(f"cannot parse {rel(p)}: {exc}")
            continue
        for parts, deferred, line in items:
            if not parts:
                continue
            if parts[0] in LAYERS:
                if len(parts) == 1:
                    if p.parent.name == "scripts" and parts[0] == "app":
                        problems.append(f"layer import {rel(p)}:{line} -> app")
                    continue
                if parts[0] == "app" and p.parent.name == "scripts":
                    problems.append(f"layer import {rel(p)}:{line} -> {'.'.join(parts)}")
                    continue
                target = by_layer.get((parts[0], parts[1]))
                targets = [target] if target else []
            else:
                targets = by_stem.get(parts[0], [])
            for target in targets:
                if target == p:
                    problems.append(f"self import {rel(p)}:{line} -> {'.'.join(parts)}")
                    continue
                if p.parent.name == "scripts" and target.parent.name == "app":
                    problems.append(f"layer import {rel(p)}:{line} -> {rel(target)}")
                    continue
                edges[p].append((target, line, deferred))
    return files, edges, problems


def cycles(edges: dict[Path, list[tuple[Path, int, bool]]]) -> list[list[Path]]:
    index = 0
    idx: dict[Path, int] = {}
    low: dict[Path, int] = {}
    stack: list[Path] = []
    on_stack: set[Path] = set()
    out: list[list[Path]] = []

    def walk(v: Path) -> None:
        nonlocal index
        idx[v] = low[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)
        for w, _, _ in edges.get(v, []):
            if w not in idx:
                walk(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], idx[w])
        if low[v] == idx[v]:
            comp: list[Path] = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                out.append(comp)

    for v in edges:
        if v not in idx:
            walk(v)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Циклы импортов и встречные слои (docs/REVIEW.md)")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    args = ap.parse_args()
    root = Path(args.root).resolve()
    sys.setrecursionlimit(10000)

    files, edges, problems = collect(root)
    rel = lambda p: p.relative_to(root).as_posix()  # noqa: E731
    print(f"check-imports: {len(files)} modules, {sum(len(v) for v in edges.values())} internal imports")

    failed = bool(problems)
    for msg in problems:
        print("FAIL " + msg)

    for comp in cycles(edges):
        failed = True
        print("FAIL cycle: " + " -> ".join(rel(x) for x in sorted(comp)))
        for x in sorted(comp):
            for target, line, _ in edges[x]:
                if target in comp:
                    print(f"  {rel(x)}:{line} -> {rel(target)}")

    for p in files:
        for target, line, deferred in edges[p]:
            if deferred:
                print(f"WARN deferred import: {rel(p)}:{line} -> {rel(target)}")

    print("OK: no violations" if not failed else "violations found")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
