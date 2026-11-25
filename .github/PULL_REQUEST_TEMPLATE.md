## Issue

Closes #

## Что изменилось

Коротко: что было, что стало, почему так.

## Как проверить

```powershell
uv run python tools/check-imports.py
uv run python -m compileall -q app scripts tools samples
uv run --with python-docx --with pypdf python app/engine.py --path samples/demo-project --out demo.json
```

Тесты:

```powershell
uv run --with-requirements requirements-dev.txt python -m pytest -q
```

## Скриншоты

Обязательны, если изменение видно на экране. Встроенные картинки, не голые ссылки.

| До | После |
|---|---|
| ![до](https://raw.githubusercontent.com/dettram/praverana/<ветка>/docs/pr-assets/<N>/00-before.png) | ![после](https://raw.githubusercontent.com/dettram/praverana/<ветка>/docs/pr-assets/<N>/01-after-1440.png) |

Для UI — 1440 и 390, изменённые состояния (пусто, ошибка, загрузка). Для отчёта — страница
DOCX/PDF с изменённым блоком. Если изменение невидимо — метка `no-visual` и объяснение.

## Данные и безопасность

- [ ] нет текстов ТНПА, документации заказчиков, персональных данных;
- [ ] нет секретов и внешних вызовов в рантайме;
- [ ] пути, upload, ZIP, subprocess проверены (если затронуты).

## Риск и откат

Что может сломаться и как откатить (revert, ветка, флаг).

## Чек-лист

- [ ] issue готова по DoR (`docs/GITHUB.md`);
- [ ] один PR — одна issue;
- [ ] тест на баг/правило или объяснение, почему автоматический тест невозможен;
- [ ] скриншоты для UI и отчёта (до/после, 1440/390);
- [ ] docs обновлены, `файл:строка` актуальны;
- [ ] diff прочитан целиком, отладочного кода нет.
