# Праверана.by brand guidelines

> For coding agents and contributors. Exported by Glyphfield from project `praverana`. Brand health 86/100 (Needs work). Tokens live in `tokens/`; logos in `logos/`.

**Каждое замечание — с нормой, файлом и страницей.**

Не библиотека норм и не ИИ-пересказ, а детерминированная проверка папки проекта: реестр ТНПА, индекс пунктов, отчёт с ограничениями вслух.

Mission: Дать инженеру проверяемый ответ до нормоконтроля: каждое замечание с нормой, файлом и страницей, а не «рекомендуем обратить внимание».

## Rules for every change

- Use the tokens in `tokens/brand.css` (or `tokens/tailwind.css`) instead of raw hex values, font names or pixel sizes.
- Text and backgrounds use the approved pairs below; never place text on a pair that fails WCAG AA.
- Use only the logo files in `logos/`; never redraw, recolor, stretch or add effects to a mark.
- No eyebrow text: never set a small uppercase or tracked label (a category, a number such as "01", or the brand name) above a headline. The headline leads; metadata that is needed goes after the content or in a footer.
- Орнамент — тонкая линия и ромб, не заливка.
- Герб, флаг и их фрагменты не используются.
- Красный — только ошибка, не декор.
- No generic placeholder copy
- No equal-sized image grid
- No random blue gradients
- No decorative evidence without a stated role

## Voice and copy

Principles: Адрес вместо оценки: что не так, где и по какой норме. · Границы вслух: что проверка не делает. · Решение остаётся инженеру: инструмент показывает, не приговаривает..

Personality: Observant, Plainspoken, Calm, Decisive.

Approved phrases:

- “Проверить папку”
- “Прочитано файлов: N из M”
- “Не проверено: расчёты, чертежи, сканы без текста”
- “Замечание — с нормой, файлом и страницей”

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

## Color

| Token | Hex | Name | Role | Share |
| --- | --- | --- | --- | --- |
| `--brand-color-ink` | `#15181A` | Тушь | Текст, знак и решительные поверхности | — |
| `--brand-color-paper` | `#FAF9F5` | Бумага | Основное поле и поверхность чтения | — |
| `--brand-color-muted` | `#F0EDE4` | Тёплая поверхность | Рабочие поверхности, карточки, тихая структура | — |
| `--brand-color-emphasis` | `#8A5F14` | Золото | Единственный акцент: выделение, действие, цифра | — |
| `--brand-color-success` | `#23694A` | Зелёный | Подтверждённые состояния и рост | — |
| `--brand-color-warning` | `#A97C22` | Золото графикой | Предупреждения и места, требующие внимания | — |
| `--brand-color-progress` | `#5D666B` | Вторичный | Вторичный текст, даты, метаданные | — |
| `--brand-color-error` | `#C8102E` | Красный | Ошибки и отменённые нормы | — |

Approved text pairs:

| Foreground | Background | Use | Ratio | WCAG |
| --- | --- | --- | --- | --- |
| ink | paper | Body text and headlines | 16.93:1 | AA pass |
| ink | muted | Text on quiet surfaces | 15.24:1 | AA pass |
| progress | paper | Secondary text and metadata | 5.57:1 | AA pass |
| ink | success | Text on soft accent fields | 2.71:1 | AA FAIL |
| paper | emphasis | Labels on the accent | 5.35:1 | AA-large pass |
| paper | error | Reversed text on deep panels | 5.58:1 | AA pass |

Semantic roles switch with light and dark mode. Prefer them to palette tokens in interfaces:

| Token | Light | Dark | Use |
| --- | --- | --- | --- |
| `--brand-background` | `paper` #FAF9F5 | `ink` #15181A | Page canvas behind everything |
| `--brand-surface` | `paper` #FAF9F5 | `ink` #15181A | Cards, panels, inputs and menus |
| `--brand-surface-muted` | `muted` #F0EDE4 | `ink.900` #2A2D2F | Quiet fills, hover rows and table headers |
| `--brand-foreground` | `ink` #15181A | `paper` #FAF9F5 | Body text, headings and icons |
| `--brand-foreground-muted` | `ink.600` #676A6C | `ink.400` #949698 | Secondary text, hints and metadata |
| `--brand-border` | `ink.100` #DCDEDF | `ink.900` #2A2D2F | Dividers, outlines and input borders |
| `--brand-primary` | `emphasis` #8A5F14 | `emphasis` #8A5F14 | Primary actions, selection and links |
| `--brand-primary-foreground` | `paper` #FAF9F5 | `paper` #FAF9F5 | Text and icons on primary |
| `--brand-focus` | `emphasis` #8A5F14 | `emphasis` #8A5F14 | Keyboard focus outline |
| `--brand-positive` | `success` #23694A | `success.600` #357959 | Success and healthy states |
| `--brand-caution` | `warning` #A97C22 | `warning` #A97C22 | Warnings that need attention |
| `--brand-negative` | `error` #C8102E | `error` #C8102E | Errors and destructive actions |


Paper white, Fog and the near-black Night form a neutral research surface. Signal blue marks the signal window: the active claim, decision or evidence, never a fill for the whole composition.

## Typography

| Role | Family | Weight | Line height | Tracking | Size token | Use |
| --- | --- | --- | --- | --- | --- | --- |
| Display | Onest | 550 | 0.96 | -0.049em (-3px) | `--brand-text-display` | Заголовки страниц и разделов, крупные цифры |
| Body | Onest | 400 | 1.5 | 0 (0px) | `--brand-text-body` | Основной текст, таблицы, интерфейс |
| Accent | Onest | 500 | 1.5 | 0 (0px) | `--brand-text-lead` | Подписи, метки, кнопки |
| Code | JetBrains Mono | 400 | 1.5 | 0 (0px) | `--brand-text-small` | Шифры норм, пути к файлам, числа прогонов |

Type scale: 16px base × 1.25 — caption 10.24px, small 12.8px, body 16px, lead 20px, h4 25px, h3 31.25px, h2 39.06px, h1 48.83px, display 61.04px.

Typesetting:

- Kerning stays on everywhere: `font-kerning: var(--brand-font-kerning)` and `font-feature-settings: var(--brand-font-feature-settings)`. Optical sizing stays `auto` unless a role fixes `opsz`.
- Track by size: display type uses `--brand-font-display-tracking` (slightly negative, about -0.01 to -0.025em); body, accent and code text stay at 0. Never add positive tracking to lowercase text.
- Size headlines from the scale, not to fill the frame. A 16:9 slide title takes about 6–8% of the frame height per line, and content slides less.

Switzer provides clear working typography; Instrument Serif adds an authored editorial voice for selected statements. Geist Mono is limited to measurements, source labels, and technical evidence.

## Logos

| File | Use on | Label |
| --- | --- | --- |
| `logos/mark-dark.svg` | light surfaces | Знак на светлом |
| `logos/mark-light.svg` | dark surfaces | Знак на тёмном |
| `logos/wordmark.svg` | light surfaces | Логотип на светлом |
| `logos/wordmark-light.svg` | dark surfaces | Логотип на тёмном |
| `logos/mark-mono.svg` | any surface | Одноцветный знак |

The mark is a four-point spark with a signal window at its center; with the Starter wordmark it sets orientation and stays small. The identity shows through selection, framing and evidence, not repeated logos.

## Graphic device and imagery

**Ромб.** Ромб — основа рушникового орнамента; в знаке он держит галочку. В макетах ромб работает как модуль сетки и как разделитель, без вышивки и без герба.

Один ромбовидный акцент на макет; текст и таблицы выравниваются по его осям.

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
| Challenge | Early product work scatters across calls, screenshots, documents and opinions. By the time the team meets to decide, nobody can point to the evidence behind a choice or say who owns the next step. |
| Central idea | One window on what matters now: the signal window frames a single piece of evidence, decision or next step, and everything else stays quiet. |
| Promise | Every view shows what we know, what we decided and who moves next. |
| Outcome | A team can see the decision in front of it, trace that decision back to evidence, and leave every review with a named owner and a date. |

Pillars:

- Evidence sits next to the claim
- One decision in focus per view
- Every next step has an owner
- Progress is written down, not remembered

## Products, audiences and proof

Products:

- Аудит папки проекта
- Отчёт DOCX/PDF
- Разметка Word
- История прогонов
- **Research board** — Pin interviews, screenshots and data next to the question they answer.
- **Decision log** — Every decision with the evidence behind it, an owner and a date.
- **Working brief** — A one-page brief that updates itself as decisions land.
- **Shareable review** — One read-only link for stakeholders, with comments on each decision.

Audiences: ГИП и главные специалисты проектных организаций, Нормоконтроль и служба качества проекта, Эксперты и заказчики, принимающие отчёт.

Proof (use only as published): 141 документ ТНПА в перечне, 44 989 пунктов в индексе; 46 документов с полным текстом в фонде, остальные проверены по статусу; Файлы не покидают машину: обработка локальная.

## Applications

| Application | Format | Intent |
| --- | --- | --- |
| Starter identity | 1600 × 1000 | A decisive opening composition built around the signal window. |
| Logo family | Responsive family | The spark mark with a signal window at its center, the wordmark and a horizontal lockup. |
| Workspace | 1440 × 1024 | A focused planning surface with blue signal states and low-noise scaffolding. |
| Launch story | 16:9 / 4:5 | One clear announcement scaled through the system. |
| Field notes | A4 / web | Research, decisions, and progress assembled as a living record. |
| Progress cards | 1:1 | Short updates that use the signal window as a consistent anchor. |
| Working deck | 16:9 | A title, argument, evidence, system, and next-step slide family. |
| Team kit | Notebook / card | Small-scale material applications that preserve the crisp window motif. |

## Before you ship

- Colors come from tokens and every text pair passes WCAG AA.
- Headlines use the Display role; body copy uses the Body role at the body step or larger.
- Each headline leads its block: no eyebrow label above it, and metadata sits after the content.
- Kerning is on, display tracking comes from the tokens, and body text is not tracked.
- Copy follows the voice principles and avoids the listed words.
- Logos are untouched files from `logos/` on the surface they were made for.
- Claims, metrics and customer names match the brand's published sources.

## Sources

- Complete example intended to be duplicated and renamed
- All copy, colors, applications, and graphic rules are editable
- Uses bundled template marks rather than a third-party identity
