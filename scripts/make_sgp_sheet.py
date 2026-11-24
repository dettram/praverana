"""Строительный генеральный план 2026-АТЛ «АТЛАС» — лист А1, М 1:500.

  uv run --with matplotlib scripts/make_sgp_sheet.py --out-dir "<проект>\\docs\\ПОС-ППР\\СГП"

Схема условная: посадка принята по ТЗ (габариты корпусов, мост 18 м, участок 1,35 га);
исходный генплан и сводный план сетей отсутствуют, привязка к местности не выполнялась.
Координаты — метры от юго-западного угла участка; лист — миллиметры А1 (594 × 841).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyArrow, Rectangle  # noqa: E402

SITE_W, SITE_H = 135.0, 100.0          # м; 13 500 м² = 1,35 га
SCALE = 500.0
MM_PER_M = 1000.0 / SCALE              # 2 мм на метр
ORIGIN = (25.0, 545.0)                 # мм, юго-западный угол участка
SHEET = (594.0, 841.0)

C_LINE = "#1a1a1a"
C_ROAD = "#d9d9d9"
C_BUILD = "#f2f2f2"
C_CRANE = "#c8d8e8"
C_STORE = "#e6efe0"
C_TMP = "#f6f0dc"
C_CABLE = "#e0d0e8"
C_NET = "#1f4e79"
C_DANGER = "#9e2b25"


def mm(x_m: float, y_m: float) -> tuple[float, float]:
    return ORIGIN[0] + x_m * MM_PER_M, ORIGIN[1] + y_m * MM_PER_M


def rect(ax, x, y, w, h, fc="none", ec=C_LINE, lw=0.8, ls="-", hatch=None, z=2, alpha=1.0):
    x0, y0 = mm(x, y)
    ax.add_patch(Rectangle((x0, y0), w * MM_PER_M, h * MM_PER_M, facecolor=fc,
                           edgecolor=ec, linewidth=lw, linestyle=ls, hatch=hatch,
                           zorder=z, alpha=alpha))


def line(ax, pts, color=C_LINE, lw=0.8, ls="-", z=3):
    xs = [mm(x, y)[0] for x, y in pts]
    ys = [mm(x, y)[1] for x, y in pts]
    ax.plot(xs, ys, color=color, linewidth=lw, linestyle=ls, zorder=z, solid_capstyle="butt")


def label(ax, x, y, text, size=7, ha="left", va="bottom", color=C_LINE, rot=0, weight="normal"):
    px, py = mm(x, y)
    ax.text(px, py, text, fontsize=size, ha=ha, va=va, color=color, rotation=rot,
            zorder=6, weight=weight, family="DejaVu Sans")


def sheet_text(ax, x, y, text, size=9, ha="left", va="bottom", weight="normal", style="normal"):
    ax.text(x, y, text, fontsize=size, ha=ha, va=va, weight=weight, style=style,
            family="DejaVu Sans", zorder=10)


def build_figure() -> plt.Figure:
    fig = plt.figure(figsize=(SHEET[0] / 25.4, SHEET[1] / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, SHEET[0])
    ax.set_ylim(0, SHEET[1])
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((20, 5), SHEET[0] - 25, SHEET[1] - 10, fill=False, lw=1.6, ec=C_LINE))
    return fig, ax


def draw_site(ax) -> None:
    rect(ax, 0, 0, SITE_W, SITE_H, ec=C_LINE, lw=2.2, z=4)
    for pts in (
        [(0, 0), (58, 0)], [(68, 0), (135, 0)],
        [(135, 0), (135, 100)], [(135, 100), (70, 100)],
        [(58, 100), (0, 100)], [(0, 100), (0, 0)],
    ):
        line(ax, pts, lw=1.6, ls=(0, (6, 3)))

    rect(ax, 0, 94, 135, 6, fc=C_ROAD, ec=C_LINE, lw=0.6)
    rect(ax, 0, 0, 135, 4, fc=C_ROAD, ec=C_LINE, lw=0.6)
    rect(ax, 0, 0, 6, 94, fc=C_ROAD, ec=C_LINE, lw=0.6)
    rect(ax, 129, 0, 6, 94, fc=C_ROAD, ec=C_LINE, lw=0.6)

    rect(ax, 6, 4, 80, 48, fc=C_BUILD, lw=2.0)
    label(ax, 46, 26, "Корпус А\n(стилобат 80 × 48 м,\nмонолит ЖБ)", ha="center", size=8)
    rect(ax, 92, 4, 36, 48, fc=C_BUILD, lw=2.0)
    label(ax, 110, 24, "Корпус Б\n(зал 36 × 48 м,\nсталь, фермы 36 м)", ha="center", size=7.5)
    rect(ax, 6, 70, 32, 24, fc=C_BUILD, lw=2.0)
    label(ax, 22, 79, "Корпус В\n(24 × 32 м,\n+23,400)", ha="center", size=7.5)
    rect(ax, 14, 52, 4.2, 18, fc="#fff2cc", ec=C_LINE, lw=1.2)
    label(ax, 21, 60, "Мост 18 м", size=6.5, rot=90)

    for (cx, cy, tag) in ((90, 26, "Ст-1"), (44, 61, "Ст-2")):
        ax.add_patch(Circle(mm(cx, cy), 20 * MM_PER_M, fill=False, ec=C_NET, lw=0.9,
                            ls="--", zorder=4))
        ax.add_patch(Circle(mm(cx, cy), 25 * MM_PER_M, fill=False, ec=C_DANGER, lw=0.9,
                            ls=":", zorder=4))
        rect(ax, cx - 2.5, cy - 2.5, 5, 5, fc=C_CRANE, ec=C_LINE, lw=0.9, z=5)
        label(ax, cx - 2.2, cy + 3, tag, size=7, weight="bold")

    rect(ax, 54, 56, 13, 10, fc=C_STORE, ec=C_LINE, lw=0.7)
    label(ax, 60.5, 59.5, "Сваи", ha="center", size=7)
    rect(ax, 69, 56, 13, 10, fc=C_STORE, ec=C_LINE, lw=0.7)
    label(ax, 75.5, 59.5, "Профнастил", ha="center", size=6.5)
    rect(ax, 96, 56, 24, 12, fc=C_STORE, ec=C_LINE, lw=0.9, ls="--")
    label(ax, 108, 60, "Стенд укрупнения\nферм 24 × 12 м", ha="center", size=6.5)
    rect(ax, 122, 70, 7, 20, fc=C_STORE, ec=C_LINE, lw=0.7)
    label(ax, 125.5, 80, "Закрытый склад", ha="center", size=6, rot=90)

    for i in range(6):
        bx = 8 + (i % 3) * 4.2
        by = 56 + (i // 3) * 5.2
        rect(ax, bx, by, 3.8, 4.6, fc=C_TMP, ec=C_LINE, lw=0.6, z=5)
    label(ax, 8, 53.5, "Бытовой городок", size=6.5)

    rect(ax, 59, 92, 3, 3, fc=C_TMP, ec=C_LINE, lw=0.7, z=5)
    label(ax, 62.5, 92.5, "КПП", size=6.5)
    rect(ax, 63, 95.5, 4, 3, fc=C_TMP, ec=C_LINE, lw=0.7, z=5)
    label(ax, 67.5, 96, "мойка колёс", size=6)
    rect(ax, 129.5, 70, 4, 6, fc=C_TMP, ec=C_LINE, lw=0.7, z=5)
    label(ax, 131.5, 76.5, "ТП, щиты", size=6, ha="center")

    rect(ax, 132, 4, 3, 90, fc=C_CABLE, ec=C_LINE, lw=0.5, hatch="///", alpha=0.8, z=3)
    label(ax, 133.5, 48, "Охранная зона кабеля 10 кВ, 3 м", size=6, rot=90, ha="center")

    line(ax, [(131, 73), (110, 73), (90, 68), (90, 28)], color=C_NET, lw=0.7, ls=(0, (4, 2)))
    line(ax, [(131, 73), (60, 73), (44, 63)], color=C_NET, lw=0.7, ls=(0, (4, 2)))
    label(ax, 92, 69, "ВЛ 0,4 кВ (временная)", size=6, color=C_NET)
    line(ax, [(60, 96), (60, 70), (44, 62)], color="#2e6b3a", lw=0.7, ls=(0, (1, 2)))
    label(ax, 61, 80, "В1 (временный ввод)", size=6, color="#2e6b3a", rot=90)

    rect(ax, -30, 26, 18, 30, fc="none", ec="#666666", lw=0.9, ls="--")
    label(ax, -21, 41, "Существующий\n9-эт. жилой дом\n(30 м от границы)", size=6, ha="center")
    rect(ax, 136, 10, 12, 60, fc="none", ec="#666666", lw=0.9, ls="--")
    label(ax, 142, 40, "Действующая производственная территория", size=6, ha="center", rot=90)
    rect(ax, 20, -14, 90, 8, fc="none", ec="#666666", lw=0.9, ls="--")
    label(ax, 65, -12.5, "ул. Калиновского (красная линия)", size=6.5, ha="center")

    sx, sy = mm(62, 110)
    ex, ey = mm(62, 97)
    ax.add_patch(FancyArrow(sx, sy, ex - sx, ey - sy, width=1.2, head_width=4,
                            head_length=5, length_includes_head=True, color=C_LINE, zorder=6))
    label(ax, 63, 104, "Въезд основной (север)", size=6.5)
    label(ax, 20, -6, "Выезд хозяйственный (юг)", size=6.5)


def draw_legend(ax) -> None:
    x, y = 320, 700
    sheet_text(ax, x, y + 20, "УСЛОВНЫЕ ОБОЗНАЧЕНИЯ", size=8.5, weight="bold")
    rows = [
        ("solid", "Граница участка — 1,35 га"),
        ("fence", "Ограждение площадки 2,0 м"),
        ("road", "Дороги, пожарные проезды 6 м"),
        ("build", "Проектируемые здания"),
        ("temp", "Временные здания, КПП"),
        ("store", "Склады, площадки, стенд"),
        ("crane", "Стоянка крана 50 т"),
        ("zone", "Опасная зона R = 25 м"),
        ("cable", "Охранная зона кабеля 10 кВ"),
        ("net", "Временные сети"),
    ]
    yy = y
    for kind, text in rows:
        if kind == "solid":
            ax.plot([x, x + 14], [yy, yy], color=C_LINE, lw=2.2)
        elif kind == "fence":
            ax.plot([x, x + 14], [yy, yy], color=C_LINE, lw=1.4, ls=(0, (6, 3)))
        elif kind == "road":
            ax.add_patch(Rectangle((x, yy - 2), 14, 4, facecolor=C_ROAD, edgecolor=C_LINE, lw=0.5))
        elif kind == "build":
            ax.add_patch(Rectangle((x, yy - 2), 14, 4, facecolor=C_BUILD, edgecolor=C_LINE, lw=1.6))
        elif kind == "temp":
            ax.add_patch(Rectangle((x, yy - 2), 14, 4, facecolor=C_TMP, edgecolor=C_LINE, lw=0.6))
        elif kind == "store":
            ax.add_patch(Rectangle((x, yy - 2), 14, 4, facecolor=C_STORE, edgecolor=C_LINE,
                                   lw=0.6, ls="--"))
        elif kind == "crane":
            ax.add_patch(Rectangle((x + 5, yy - 2), 4, 4, facecolor=C_CRANE, edgecolor=C_LINE, lw=0.8))
        elif kind == "zone":
            ax.add_patch(Circle((x + 7, yy), 4, fill=False, edgecolor=C_DANGER, lw=0.8, ls=":"))
        elif kind == "cable":
            ax.add_patch(Rectangle((x, yy - 2), 14, 4, facecolor=C_CABLE, edgecolor=C_LINE,
                                   lw=0.5, hatch="///"))
        elif kind == "net":
            ax.plot([x, x + 14], [yy, yy], color=C_NET, lw=0.8, ls=(0, (4, 2)))
        sheet_text(ax, x + 20, yy - 2.4, text, size=7)
        yy -= 11


def table_simple(ax, x, y, title, headers, rows, widths, row_h=8, size=6.5):
    total_w = sum(widths)
    n = len(rows) + 1
    height = row_h * n
    sheet_text(ax, x, y + height + 4, title, size=8, weight="bold")
    ax.add_patch(Rectangle((x, y), total_w, height, fill=False, lw=1.0, ec=C_LINE))
    acc = 0
    for w in widths[:-1]:
        acc += w
        ax.plot([x + acc, x + acc], [y, y + height], color=C_LINE, lw=0.6)
    for r in range(n + 1):
        ax.plot([x, x + total_w], [y + r * row_h, y + r * row_h], color=C_LINE, lw=0.6)
    for i, h in enumerate(headers):
        off = sum(widths[:i])
        sheet_text(ax, x + off + 1.2, y + height - row_h + 2, h, size=size, weight="bold")
    for r, row in enumerate(rows):
        yy = y + height - row_h * (r + 2) + 2
        for i, cell in enumerate(row):
            off = sum(widths[:i])
            sheet_text(ax, x + off + 1.2, yy, cell, size=size)
    return height


def draw_tables(ax) -> None:
    h1 = table_simple(
        ax, 25, 392, "ВЕДОМОСТЬ ЗДАНИЙ И СООРУЖЕНИЙ",
        ("№", "Наименование", "Габариты, м", "Этаж-ть", "Площадь, м²"),
        (("1", "Корпус А — стилобат", "80,0 × 48,0", "2–3", "3 840"),
         ("2", "Корпус Б — зал", "36,0 × 48,0", "1 + ант.", "1 728"),
         ("3", "Корпус В — башня", "24,0 × 32,0", "5", "768"),
         ("4", "Мост-вирендель", "18,0 × 4,2", "—", "76"),
         ("", "Итого застройка", "", "", "6 412")),
        widths=(9, 76, 46, 26, 33), row_h=8)

    table_simple(
        ax, 25, 288, "ПОТРЕБНОСТЬ В ОСНОВНЫХ МАШИНАХ",
        ("Машина", "Параметр", "Кол-во"),
        (("Кран гусеничный", "50 т, вылет 20 м", "1"),
         ("Кран автомобильный", "25 т", "1"),
         ("Копёр (свайный агрегат)", "—", "1"),
         ("Автобетононасос", "—", "1"),
         ("Экскаватор гусеничный", "1,2 м³", "1"),
         ("Самосвал", "20 т", "6")),
        widths=(96, 66, 28), row_h=8)

    data = (
        ("Площадь участка", "13 500 м² (1,35 га)"),
        ("Площадь застройки", "6 412 м² (47,5 %)"),
        ("Покрытия и площадки", "≈ 3 700 м² (по чертежу)"),
        ("Озеленение", "≥ 30 % (4 050 м²)"),
        ("Протяжённость ограждения", "470 м"),
        ("Опасные зоны крана", "R = 25 м (2 стоянки)"),
    )
    height = 7
    x2, y2 = 320, 392
    total_w = 250
    sheet_text(ax, x2, y2 + height * (len(data) + 1) + 4, "ОСНОВНЫЕ ПОКАЗАТЕЛИ", size=8,
               weight="bold")
    ax.add_patch(Rectangle((x2, y2), total_w, height * (len(data) + 1), fill=False, lw=1.0,
                           ec=C_LINE))
    for r in range(len(data) + 2):
        ax.plot([x2, x2 + total_w], [y2 + r * height, y2 + r * height], color=C_LINE, lw=0.6)
    ax.plot([x2 + 120, x2 + 120], [y2, y2 + height * (len(data) + 1)], color=C_LINE, lw=0.6)
    for r, (k, v) in enumerate(data):
        yy = y2 + height * (len(data) - r)
        sheet_text(ax, x2 + 1.5, yy, k, size=6.5)
        sheet_text(ax, x2 + 121.5, yy, v, size=6.5)

    table_simple(
        ax, 25, 60, "КАЛЕНДАРНЫЙ ПЛАН РАБОТ ПОДГОТОВИТЕЛЬНОГО ПЕРИОДА",
        ("Код", "Работа", "Месяц"),
        (("П-1", "Ограждение, временные дороги, мойка колёс", "1"),
         ("П-2", "Бытовой городок, склады, стенд укрупнения", "1"),
         ("П-3", "Геодезическая разбивочная основа, вынос осей", "1"),
         ("П-4", "Вертикальная планировка, поверхностный водоотвод", "1–2"),
         ("П-5", "Временные сети: электро, вода, освещение", "1–2"),
         ("П-6", "Обследование зданий в зоне влияния, маяки", "1–2")),
        widths=(16, 134, 30), row_h=8)

    sheet_text(ax, 25, 272, "ПРИМЕЧАНИЯ", size=8, weight="bold")
    notes = [
        "1. Посадка зданий принята по ТЗ 2026-АТЛ; исходный генплан и сводный план сетей отсутствуют.",
        "2. Лист не является основанием для разбивки: основа создаётся по СН 1.03.02-2019.",
        "3. Работа крана вблизи жилого дома — с ограничением вылета и защитным экраном (ППР).",
        "4. Земляные работы в охранной зоне кабеля 10 кВ — по наряду-допуску и с представителем сети.",
        "5. Пожарный проезд 6 м по северу, западу и востоку; юг — по ул. Калиновского.",
        "6. Склады и стенд укрупнения размещены в зоне действия крана (стоянка Ст-1).",
        "7. Временные сети и бытовой городок — по ППР; точки подключения уточняются по ТУ.",
    ]
    for i, t in enumerate(notes):
        sheet_text(ax, 25, 258 - i * 6.5, t, size=6.5)


def draw_agreement(ax) -> None:
    x, y, w, h = 320, 150, 250, 42
    sheet_text(ax, x, y + h + 4, "СОГЛАСОВАНО", size=8, weight="bold")
    ax.add_patch(Rectangle((x, y), w, h, fill=False, lw=1.0, ec=C_LINE))
    rows = (("Заказчик", "УКС г. Минска", "_________________"),
            ("Генподрядчик", "не определён", "_________________"),
            ("Субподряд (сети)", "по договору", "_________________"))
    row_h = h / len(rows)
    for r, (role, org, sign) in enumerate(rows):
        yy = y + h - row_h * (r + 1) + 3
        sheet_text(ax, x + 2, yy, role, size=6.5)
        sheet_text(ax, x + 45, yy, org, size=6.5)
        sheet_text(ax, x + 150, yy, sign, size=6.5)
    ax.plot([x, x + w], [y + h - row_h, y + h - row_h], color=C_LINE, lw=0.6)
    ax.plot([x, x + w], [y + h - 2 * row_h, y + h - 2 * row_h], color=C_LINE, lw=0.6)


def draw_stamp(ax) -> None:
    x0, y0, w, h = 389, 5, 185, 55
    ax.add_patch(Rectangle((x0, y0), w, h, fill=False, lw=1.4, ec=C_LINE, zorder=10))
    for dx in (7, 17, 47, 57, 100, 148):
        ax.plot([x0 + dx, x0 + dx], [y0, y0 + h], color=C_LINE, lw=0.7, zorder=10)
    for dy in (40, 30, 20, 10):
        ax.plot([x0, x0 + 100], [y0 + dy, y0 + dy], color=C_LINE, lw=0.7, zorder=10)
    ax.plot([x0 + 100, x0 + w], [y0 + 30, y0 + 30], color=C_LINE, lw=0.7, zorder=10)
    ax.plot([x0 + 100, x0 + w], [y0 + 15, y0 + 15], color=C_LINE, lw=0.7, zorder=10)

    for i, t in enumerate(("Изм.", "Лист", "№ докум.", "Подп.", "Дата")):
        xx = (x0 + 1.5, x0 + 8.5, x0 + 18.5, x0 + 48.5, x0 + 58.5)[i]
        sheet_text(ax, xx, y0 + 41, t, size=5.5)
    for i, (role, who) in enumerate((("Разраб.", "инженер-технолог"), ("Пров.", "ГИП"),
                                     ("Н. контр.", ""), ("Утв.", "заказчик"))):
        yy = y0 + 31 - i * 10
        sheet_text(ax, x0 + 1.5, yy, role, size=5.5)
        sheet_text(ax, x0 + 18.5, yy, who, size=5.5)

    sheet_text(ax, x0 + 102, y0 + 42, "2026-АТЛ-СГП-01", size=8, weight="bold")
    sheet_text(ax, x0 + 102, y0 + 33, "Многофункциональный научно-просветительский", size=5.5)
    sheet_text(ax, x0 + 102, y0 + 29.5, "центр «АТЛАС», г. Минск", size=5.5)
    sheet_text(ax, x0 + 102, y0 + 21, "Строительный генеральный план", size=7, weight="bold")
    sheet_text(ax, x0 + 102, y0 + 16.5, "Стадия: строительный проект", size=5.5)
    sheet_text(ax, x0 + 102, y0 + 9, "Лист 1", size=6.5)
    sheet_text(ax, x0 + 155, y0 + 9, "Листов 1", size=6.5)
    sheet_text(ax, x0 + 102, y0 + 3, "М 1:500", size=6.5)
    sheet_text(ax, x0 + 155, y0 + 3, "Формат А1", size=6.5)


def draw_scale_and_north(ax) -> None:
    x0, y0 = 25, 518
    for i in range(5):
        ax.add_patch(Rectangle((x0 + i * 20, y0), 20, 2.4,
                               facecolor=C_LINE if i % 2 == 0 else "white",
                               edgecolor=C_LINE, lw=0.5))
    for i, val in enumerate((0, 10, 20, 30, 40, 50)):
        sheet_text(ax, x0 + i * 20 - 1, y0 - 5, str(val), size=6.5)
    sheet_text(ax, x0, y0 + 4, "Масштаб 1:500 (в 1 см — 5 м)", size=7)

    ax.add_patch(FancyArrow(545, 770, 0, 20, width=1.2, head_width=6, head_length=7,
                            color=C_LINE, zorder=10))
    sheet_text(ax, 545, 795, "С", size=11, ha="center", weight="bold")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    fig, ax = build_figure()

    sheet_text(ax, 25, 812, "СТРОИТЕЛЬНЫЙ ГЕНЕРАЛЬНЫЙ ПЛАН", size=13, weight="bold")
    sheet_text(ax, 25, 802, "2026-АТЛ — Многофункциональный научно-просветительский центр «АТЛАС»",
               size=9)
    sheet_text(ax, 25, 793,
               "г. Минск, Первомайский район, участок 2026/П-14 (адрес условный). "
               "Стадия: строительный проект.", size=7.5)

    draw_site(ax)
    draw_legend(ax)
    draw_tables(ax)
    draw_agreement(ax)
    draw_scale_and_north(ax)
    draw_stamp(ax)

    png = out / "2026-АТЛ-СГП-01.png"
    pdf = out / "2026-АТЛ-СГП-01.pdf"
    fig.savefig(str(png), dpi=150, facecolor="white")
    fig.savefig(str(pdf), facecolor="white")
    plt.close(fig)
    print(f"written: {pdf}")
    print(f"written: {png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
