# Кит лендинга

Минимальный набор из **design-taste-frontend 2.5.1** — MIT,
[github.com/Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill).
Скопирован 25.11.2026 только в объёме, который использует `app/ui/landing.html`;
демо, фотографии и сборочные файлы кита не входят.

| Файл | Зачем |
|---|---|
| `system.css`, `system.js` | база кита: сетка, типографика, поведение |
| `ui/base.css`, `ui/cards.css`, `ui/ui.js` | примитивы и карточки |
| `motion/motion.css`, `motion/motion.js` | вход и hover |
| `backgrounds/backgrounds.css`, `backgrounds/backgrounds.js` | фон лендинга |
| `layout/layout.css`, `layout/layout.js` | раскладка секций |
| `icons/icon.css` | иконки |
| `moments/moments.js`, `moments/lib.js`, `moments/cursor-spotlight/*` | момент `cursor-spotlight` |

Полный кит (включая демо и галереи) ставится `tools/setup-kit.ps1` в отслеживаемую
папку `app/ui/assets` — в git он попадает. После обновления кита проверь
`uv run python tools/check-assets.py` и гейт лендинга.

Лицензия кита — MIT; исходный текст: <https://github.com/Leonxlnx/taste-skill/blob/main/LICENSE>.
