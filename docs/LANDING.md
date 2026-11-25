# Сборка лендинга: кит design-taste-frontend

`app/ui/landing.html` собран на ките `design-taste-frontend` (system.css, layout, motion,
backgrounds, moments). Файлы кита в репозиторий не входят — у них своя лицензия, и они
обновляются вместе со скиллом.

Если кит установлен локально (например, как скилл OpenCode), скопируйте ассеты одной командой:

```powershell
# путь к киту — папка, где лежат assets/system.css и scripts/gate.mjs
powershell -File tools/setup-kit.ps1 -SkillPath "$env:USERPROFILE\.config\opencode\skill\design-taste-frontend"
```

Скрипт копирует только нужные папки в `app/ui/assets/` и ничего не перезаписывает, кроме них.

## Проверки страницы

```powershell
$env:PATH = "$env:LOCALAPPDATA\node22;$env:PATH"   # Node 22
$env:CHROME_PATH = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
cd app\ui

node <kit>\scripts\copy-lint.mjs landing.html --kind software
node <kit>\scripts\consistency.mjs "http://127.0.0.1:8765/" --widths 1440,390 `
     --rhythm-widths 1440,390 --profile .taste-skill/chrome-check `
     --page software --category "аудит проектной документации" --primary "Проверить папку проекта"
node <kit>\scripts\gate.mjs --start "http://127.0.0.1:8765/" --kind software `
     --category "аудит проектной документации" --primary "Проверить папку проекта"
node <kit>\scripts\gate.mjs
```

Текущее состояние: **GATE: PASS**, copy-lint 0 FAIL, consistency 0 FAIL на 1440, 390 и обходе 320.
Waiver'ы — в `.taste-skill/waivers.json` (только `hero-lines` и `hero-maxchars`: чекер подставляет
45 знаков вместо фактических 26 в заголовке). После обновления знака (25.11.2026) — 11 WARN, 0 FAIL.
