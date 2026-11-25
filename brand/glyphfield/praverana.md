# Праверана.by brand guidelines

> For coding agents and contributors. Exported by Glyphfield from project `praverana`. Brand health 100/100 (Strong). Tokens live in `tokens/`; logos in `logos/`.

**Каждое замечание — с нормой, файлом и страницей.**

Не библиотека норм и не ИИ-пересказ, а детерминированная проверка папки проекта: реестр ТНПА, индекс пунктов, отчёт с ограничениями вслух.

Mission: Дать инженеру проверяемый ответ до нормоконтроля: каждое замечание с нормой, файлом и страницей, а не «рекомендуем обратить внимание».

## Rules for every change

- Use the tokens in `tokens/brand.css` (or `tokens/tailwind.css`) instead of raw hex values, font names or pixel sizes.
- Text and backgrounds use the approved pairs below; never place text on a pair that fails WCAG AA.
- Keep the palette in proportion: the dominant field stays dominant and the accent stays rare.
- Use only the logo files in `logos/`; never redraw, recolor, stretch or add effects to a mark.
- No eyebrow text: never set a small uppercase or tracked label (a category, a number such as "01", or the brand name) above a headline. The headline leads; metadata that is needed goes after the content or in a footer.
- Орнамент — только во вспомогательных полосах, не в знаке.
- Герб, флаг и их фрагменты не используются.
- Красный — только ошибка, не декор.
- Золото — только в надписи и акцентах; в знаке его нет.
- Avoid: Герб и флаг
- Avoid: Градиентные фоны
- Avoid: Стоковые люди
- Avoid: Красный как декор
- Avoid: Обещание полной проверки проекта

## Voice and copy

Principles: Адрес вместо оценки: что не так, где и по какой норме. · Границы вслух: что проверка не делает. · Решение остаётся инженеру: инструмент показывает, не приговаривает..

Personality: Точный, Сдержанный, Прямой, Спокойный.

Approved phrases:

- “Проверить папку”
- “Прочитано файлов: N из M”
- “Не проверено: расчёты, чертежи, сканы без текста”
- “Открыть в документе”

Avoid:

- инновационный
- экосистема
- под ключ
- команда профессионалов
- мы гарантируем соответствие
- полная проверка проекта

| Context | Write | Avoid |
| --- | --- | --- |
| Пустой результат | Выполненные проверки замечаний не выявили. Это не заключение экспертизы. | Ошибок нет! |
| Ошибка доступа | Нет доступа к папке. Проверьте права или выберите другую. | PermissionError: [WinError 5] |
| Скан без текста | В файле нет текстового слоя: он не читался и в покрытие не вошёл. | Файл проверен |
| Ограничение проверки | Проверены текст, шифры и комплектность. Расчёты и чертежи не проверялись. | Проект полностью проверен |

## Color

| Token | Hex | Name | Role | Share |
| --- | --- | --- | --- | --- |
| `--brand-color-ink` | `#15181A` | Тушь | Текст, знак и решительные поверхности | 24% |
| `--brand-color-paper` | `#FAF9F5` | Бумага | Основное поле и поверхность чтения | 58% |
| `--brand-color-muted` | `#F0EDE4` | Тёплая поверхность | Рабочие поверхности, карточки, тихая структура | 8% |
| `--brand-color-emphasis` | `#8A5F14` | Золото | Единственный акцент: выделение, действие, цифра | 5% |
| `--brand-color-success` | `#23694A` | Зелёный | Подтверждённые состояния и рост | 1% |
| `--brand-color-warning` | `#A97C22` | Золото в графике | Предупреждения и места, требующие внимания | 1% |
| `--brand-color-progress` | `#5D666B` | Вторичный | Вторичный текст, даты, метаданные | 2% |
| `--brand-color-error` | `#C8102E` | Красный | Ошибки и отменённые нормы | 1% |

Approved text pairs:

| Foreground | Background | Use | Ratio | WCAG |
| --- | --- | --- | --- | --- |
| ink | paper | Основной текст и заголовки | 16.93:1 | AA pass |
| ink | muted | Текст на рабочих поверхностях | 15.24:1 | AA pass |
| ink | warning | Текст на предупреждающей плашке | 4.75:1 | AA pass |
| progress | paper | Вторичный текст, даты, метаданные | 5.57:1 | AA pass |
| progress | muted | Метаданные на карточках | 5.01:1 | AA pass |
| emphasis | paper | Акцентный текст и ссылки | 5.35:1 | AA pass |
| emphasis | muted | Акцент на рабочей поверхности | 4.81:1 | AA pass |
| success | paper | Подтверждённые состояния | 6.25:1 | AA pass |
| error | paper | Ошибки и отменённые нормы | 5.58:1 | AA pass |
| paper | ink | Текст на тёмных поверхностях | 16.93:1 | AA pass |
| paper | emphasis | Текст на акцентной плашке | 5.35:1 | AA pass |
| paper | success | Текст на зелёной плашке | 6.25:1 | AA pass |
| paper | error | Текст на красной плашке | 5.58:1 | AA pass |

Semantic roles switch with light and dark mode. Prefer them to palette tokens in interfaces:

| Token | Light | Dark | Use |
| --- | --- | --- | --- |
| `--brand-background` | `paper` #FAF9F5 | `ink` #15181A | Page canvas behind everything |
| `--brand-surface` | `muted` #F0EDE4 | `ink` #15181A | Cards, panels, inputs and menus |
| `--brand-surface-muted` | `muted` #F0EDE4 | `ink` #15181A | Quiet fills, hover rows and table headers |
| `--brand-foreground` | `ink` #15181A | `paper` #FAF9F5 | Body text, headings and icons |
| `--brand-foreground-muted` | `progress` #5D666B | `muted` #F0EDE4 | Secondary text, hints and metadata |
| `--brand-border` | `muted` #F0EDE4 | `progress` #5D666B | Dividers, outlines and input borders |
| `--brand-primary` | `emphasis` #8A5F14 | `emphasis` #8A5F14 | Primary actions, selection and links |
| `--brand-primary-foreground` | `paper` #FAF9F5 | `paper` #FAF9F5 | Text and icons on primary |
| `--brand-focus` | `emphasis` #8A5F14 | `emphasis` #8A5F14 | Keyboard focus outline |
| `--brand-positive` | `success` #23694A | `success` #23694A | Success and healthy states |
| `--brand-caution` | `warning` #A97C22 | `warning` #A97C22 | Warnings that need attention |
| `--brand-negative` | `error` #C8102E | `error` #C8102E | Errors and destructive actions |

Fix before use:

- dark: positive on background is 2.71:1 (needs 3:1)

Бумага и тушь держат поле; золото — единственный акцент, красный — только ошибка, зелёный — подтверждение.

## Typography

| Role | Family | Weight | Line height | Tracking | Size token | Use |
| --- | --- | --- | --- | --- | --- | --- |
| Display | Onest | 550 | 1.08 | -0.02em (-1.2px) | `--brand-text-display` | Заголовки страниц и разделов, крупные цифры |
| Body | Onest | 400 | 1.55 | 0 (0px) | `--brand-text-body` | Основной текст, таблицы, интерфейс |
| Accent | Onest | 500 | 1.3 | 0 (0px) | `--brand-text-lead` | Подписи, метки, кнопки |
| Code | JetBrains Mono | 400 | 1.45 | 0 (0px) | `--brand-text-small` | Шифры норм, пути к файлам, числа прогонов |

Type scale: 16px base × 1.25 — caption 10.24px, small 12.8px, body 16px, lead 20px, h4 25px, h3 31.25px, h2 39.06px, h1 48.83px, display 61.04px.

Typesetting:

- Kerning stays on everywhere: `font-kerning: var(--brand-font-kerning)` and `font-feature-settings: var(--brand-font-feature-settings)`. Optical sizing stays `auto` unless a role fixes `opsz`.
- Track by size: display type uses `--brand-font-display-tracking` (slightly negative, about -0.01 to -0.025em); body, accent and code text stay at 0. Never add positive tracking to lowercase text.
- Size headlines from the scale, not to fill the frame. A 16:9 slide title takes about 6–8% of the frame height per line, and content slides less.

Font files:

- Onest Variable, кириллица (woff2) — OFL-1.1 → `fonts/cyrillic-wght-normal.woff2`
- JetBrains Mono 400, кириллица (woff2) — OFL-1.1 → `fonts/cyrillic-400-normal.woff2`

Onest для текста и заголовков, JetBrains Mono для шифров норм, путей и чисел; в DOCX — Times New Roman.

## Logos

| File | Use on | Label |
| --- | --- | --- |
| `logos/mark-dark.svg` | light surfaces | Знак на светлом |
| `logos/mark-light.svg` | dark surfaces | Знак на тёмном |
| `logos/wordmark.svg` | light surfaces | Логотип на светлом |
| `logos/wordmark-light.svg` | dark surfaces | Логотип на тёмном |
| `logos/mark-mono.svg` | any surface | Одноцветный знак |

Горизонтальный логотип в шапке, знак — для вкладки и мелких размеров; на тёмном — инверсия.

## Graphic device and imagery

**Штамп-П.** Квадратная плашка с вырезанной буквой П: печать проверки и имя продукта в одном знаке. Плашка ставится один раз, как отметка «проверено», без галочек и орнамента.

Один штамп на макет; текст и таблицы выравниваются по его краям, а не по центру.

Imagery: Документы и интерфейс крупно, без стоковых людей и офисных метафор.

## Using the brand in code

```css
@import "./tokens/brand.css";

body {
  background: var(--brand-background);
  color: var(--brand-foreground);
  font: var(--brand-font-body-weight) var(--brand-text-body) / var(--brand-font-body-leading) var(--brand-font-body);
  font-kerning: var(--brand-font-kerning);
  font-feature-settings: var(--brand-font-feature-settings);
  font-optical-sizing: var(--brand-font-optical-sizing);
}

h1 {
  font-family: var(--brand-font-display);
  font-size: var(--brand-text-display);
  font-weight: var(--brand-font-display-weight);
  line-height: var(--brand-font-display-leading);
  letter-spacing: var(--brand-font-display-tracking);
}
```

With Tailwind CSS v4, `@import "./tokens/tailwind.css";` after `@import "tailwindcss";` and use classes such as `bg-background text-foreground bg-primary font-display text-display rounded-brand`; the semantic colours switch with dark mode.

## Strategy

|  |  |
| --- | --- |
| Challenge | Замечания к проекту живут в переписке и памяти: к нормоконтролю никто не может показать, какая норма нарушена, в каком файле и на какой странице. |
| Central idea | Проверяемое замечание: одна строка — норма, файл, фрагмент, и честная граница проверки рядом. |
| Promise | Каждое замечание можно открыть в документе и сверить с пунктом нормы. |
| Outcome | Инженер приходит на нормоконтроль с отчётом, где у каждого замечания есть адрес, а у каждой проверки — граница. |

Pillars:

- Адрес вместо оценки
- Границы вслух
- Решение за инженером
- Локальная обработка

## Products, audiences and proof

Products:

- **Аудит папки проекта** — Читает DOCX и PDF в папке и сверяет шифры норм, пункты и комплектность.
- **Отчёт DOCX/PDF** — Замечания с нормой, файлом и фрагментом, плюс покрытие и границы проверки.
- **Разметка Word** — Комментарии к найденным местам в копии документа, текст не правится.
- **История прогонов** — Что проверялось, когда и с каким результатом — по каждому объекту.

Audiences: ГИП и главные специалисты проектных организаций, Нормоконтроль и служба качества проекта, Эксперты и заказчики, принимающие отчёт.

Proof (use only as published): 141 документ ТНПА в перечне, 44 989 пунктов в индексе; 46 документов с полным текстом в фонде, остальные проверены по статусу; Файлы не покидают машину: обработка локальная.

## Applications

| Application | Format | Intent |
| --- | --- | --- |
| Логотип | SVG, 16–512 px | Горизонтальный, вертикальный, монохром, знак для вкладки. |
| Отчёт аудита | DOCX / PDF, A4 | Times New Roman, шапка с объектом, таблица замечаний с нормой и фрагментом. |
| Разметка Word | DOCX + ZIP | Комментарии к фрагментам исходного документа, текст не правится. |
| Инструмент | 1440 × 1024 | Папка, покрытие, таблица замечаний, выгрузка отчёта и разметки. |
| Лендинг | 1440 / 390 | Один экран — одна мысль: слоган, пример замечания, границы. |
| Соцкарточка | 1080 × 1080 | Слоган и знак на плоском фоне, без градиентов. |
| Превью ссылки | 1200 × 630 | «Проект проверен. Праверана.» и домен. |
| Документация | Markdown | brand.md и токены для агентов и разработки. |

## Before you ship

- Colors come from tokens and every text pair passes WCAG AA.
- Headlines use the Display role; body copy uses the Body role at the body step or larger.
- Each headline leads its block: no eyebrow label above it, and metadata sits after the content.
- Kerning is on, display tracking comes from the tokens, and body text is not tracked.
- Copy follows the voice principles and avoids the listed words.
- Logos are untouched files from `logos/` on the surface they were made for.
- Claims, metrics and customer names match the brand's published sources.

## Sources

- Реестр ТНПА и индекс пунктов: corpus/ (747 файлов, 141 документ в перечне)
- Логотип и палитра: app/ui/assets/logo, app/ui/assets/tokens.css
- Шрифты Onest и JetBrains Mono: OFL-1.1, локальные woff2 в app/ui/assets/fonts
- Скриншоты: app/ui/assets/img (лендинг, инструмент, бренд-бук)
