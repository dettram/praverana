# Шрифты в интерфейсе

Оба шрифта — SIL Open Font License 1.1, полный текст в `OFL.txt`.

| Шрифт | Файлы | Источник | Лицензия |
|---|---|---|---|
| Onest (variable 100–900) | `*-wght-normal.woff2` (cyrillic, cyrillic-ext, latin, latin-ext) | Google Fonts / fontsource | OFL 1.1 |
| JetBrains Mono (400, 500) | `*-400-normal.woff2`, `*-500-normal.woff2` (cyrillic, latin) | JetBrains | OFL 1.1 |

Подключение — `fonts.css` (`@font-face`), внешних запросов нет: страница не ходит в Google.

Обновить файлы можно так:

```powershell
$base = "https://cdn.jsdelivr.net/fontsource/fonts"
# onest:vf@latest/{subset}-wght-normal.woff2
# jetbrains-mono@latest/{subset}-{400|500}-normal.woff2
```
