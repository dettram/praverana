# Инструменты дизайна: Glyphfield и DesignHub

Оба — локальные open-source студии (MIT). Оценены и использованы 25.11.2026.

## Glyphfield

`Kevin-Liu-01/Glyphfield` · local-first студия бренда: одна запись идентичности → активы, токены,
brand book, фоны. Запуск локально (Node 22, pnpm, порт 3013).

Клон — `%LOCALAPPDATA%\design-tools\glyphfield` (не Temp); `tools/glyphfield.ps1` берёт его оттуда
и откатывается на Temp, если папки нет. Порт **3013**: 3012 занимает dev-gateway Nodus
(`apps/gateway/dist/main.js`, `GATEWAY_PORT=3012`), его не трогаем.

**Запуск (detached, переживает закрытие консоли):**

```powershell
powershell -ExecutionPolicy Bypass -File tools/glyphfield.ps1 -Action start   # http://localhost:3013/studio
powershell -ExecutionPolicy Bypass -File tools/glyphfield.ps1 -Action status
powershell -ExecutionPolicy Bypass -File tools/glyphfield.ps1 -Action stop
```

Открывать через `localhost`, не `127.0.0.1`: Next.js блокирует cross-origin запросы к dev-ресурсам
(HMR, шрифты) и студия теряет горячую перезагрузку. Для API разницы нет.


**Как использован:**

| Шаг | Что сделано |
|---|---|
| идентичность | brand-запись «Праверана.by»: 8 цветов с пропорциями 60/30/10, 13 пар контраста, Onest + JetBrains Mono (8 файлов woff2 с лицензией), голос с 4 примерами, 4 продукта с описаниями, 3 скриншота, 5 логотип-слотов (data URL наших SVG) |
| аудит | `POST /api/brand/validate` → **health 100/100, «Strong»**, 0 ошибок и 0 замечаний |
| кит | `POST /api/brand/kit` → `brand/glyphfield/praverana.{css,tokens.json,tailwind.css,md}` |
| фоны | `POST /api/generate` (kind=background, style=pattern) → точки для превью 1200×630 и сетка для соцкарточки |
| сборка | финальные SVG: фон из генератора + наш знак, заголовок и слоган (типографика под контролем, не генератор) |

**Что взяли:** палитру с ролями, DTCG-токены, brand.md, паттерн-фоны, превью ссылки и соцкарточку.

**Что отклонили:** стили `gradient | grain-gradient | dither` — дают туманное золото и против
правила «плоская поверхность». Логотип генератор не рисует: слоты принимают наши файлы, это
правильно — знак должен значить, а не генерироваться.

**Что пришлось переписать:** стартовая запись содержала английские strategy, dossier, applications
и productDetails из шаблона Glyphfield. Все разделы заменены нашими (стратегия, досье, 8
применений, 4 продукта) — иначе кит отдавал бы чужой текст.

## DesignHub

`yakew7/DesignHub` · local-first набор: бренд, логотип, мокапы, соцсети, бренд-бук, токены.

**Что смотрели:** `lib/brand/logo.ts` — детерминированный авто-знак из имени (hash → одна из 4
геометрических форм) и `lib/logo/variants.ts` — набор вариантов логотипа.

**Решение:** авто-знак не берём. Случайная геометрия из имени не связана ни с проверкой, ни с
Беларусью; наш штамп с вырезанной буквой П — осмысленный
и уже работает в интерфейсе. Набор вариантов (горизонтальный, вертикальный, монохром, инверсия,
фавикон) у нас есть в `app/ui/assets/logo/`.

**Что взяли (#26):**

- **print-check** — `tools/check-logos.py`: проверяет viewBox, width/height и отсутствие живого
  текста, печатает таблицу «экран / печать / фон»; она же стоит в бренд-буке, раздел 8.
- **мокапы** — `tools/make-mockups.py`: визитка 90 × 50, шапка документа A4 и аватар 512 × 512
  из существующих файлов логотипа, без стоковых фото и 3D; показаны в бренд-буке.

**Что не берём:** авто-знак из имени и генератор «красивых» вариантов — знак должен значить,
а не выбираться хешем.

## Снимки отчёта для лендинга

Кадры отчёта и разметки пересобираются из текущего прогона, чтобы не расходиться с демо:

```powershell
uv run --with pymupdf python tools/render-report-png.py `
    --project C:/Users/Public/Projects/ATLAS-TZ --out app/ui/assets/img
```

- прогон → `/api/report/{job}.pdf` → `report-page.png` и `report-page-2.png` (935 × 1210);
- `/api/marked/{job}.zip` → Word, `ExportAsFixedFormat` с `wdExportDocumentWithMarkup` →
  `marked-page.png` (примечания видны);
- проект запускать из нейтральной папки (`C:\Users\Public\Projects\ATLAS-TZ`), иначе личный путь
  попадёт в снимок; требует установленного Word.

## Иконки приложения

```powershell
uv run --with pillow python tools/render-favicons.py
```

- `assets/icons/favicon-16/32/48.png`, `favicon.ico` (16/32/48) — вкладка;
- `apple-touch-icon-180.png` — iOS, полноразмерная бумажная подложка;
- `favicon-192.png` / `favicon-512.png` — Android, `purpose: any maskable`, знак в безопасной зоне;
- `safari-pinned-tab.svg` — чёрный контур (плашка с вырезанной П);
- `assets/manifest.webmanifest` — отдаётся сервером по `/manifest.webmanifest`
  (`application/manifest+json`); ссылки и `theme-color` есть на `/`, `/app`, `/brand`, `/review`.

## Итог

- Логотип и знак — наши (штамп с буквой П), проверены в системе бренда Glyphfield.
- Система (цвет, тип, токены, голос) — зафиксирована в Glyphfield и выгружена в репозиторий.
- Витрина (OG, соцкарточка, бренд-бук) — из Glyphfield + наша типографика.


