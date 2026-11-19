# Настройка

[English](configuration.md) · [README](../README.ru.md)

## Файлы настроек

Настройки лежат в двух файлах формата INI:

- `~/.config/adbm/config.ini` действует для всех проектов (`$XDG_CONFIG_HOME/adbm/`, если переменная задана);
- `.adbm/config.ini` в корне проекта действует только для этого проекта и перекрывает общий файл.

```bash
adbm config                                    # итоговые значения и откуда они взяты
adbm config --set devices.apis=28,33,35 --project   # одно значение в файл проекта
adbm config --set adbm-eyes.model=sonnet       # одно значение в общий файл
adbm config --init                             # общий файл со всеми ключами и комментариями
adbm config --init --project                   # файл проекта: ключи закомментированы и ничего не перекрывают
```

`--set` сохраняет комментарии и остальные ключи. Ошибку в файле показывают `adbm config` и `adbm doctor`
строкой с `!`. Ошибочное значение не применяется, вместо него действует значение по умолчанию.

## Уровни API

```ini
[devices]
apis = 28, 33, 35               # пусто — один запущенный эмулятор или API 35
image = google_apis             # вариант образа для новых AVD; не задан — любой уже скачанный телефонный
profile = pixel_8               # профиль новых AVD, см. avdmanager list device
```

Команды для нескольких устройств берут список `apis`, если не указать `--api` или `--serial`.
Запусти эмуляторы из списка через `adbm devices --start`. Команда для одного устройства выберет
запущенное устройство или попросит уточнить выбор. Общий список храни в `~/.config/adbm/config.ini`.
Пустой `apis` в проекте не отменяет общий список.

При первой проверке в проекте `apis` пустой. Агент смотрит `minSdk` приложения, предлагает уровни
с причинами и ждёт ответа. Затем он записывает ответ: `adbm config --set devices.apis=28,33,35 --project`.
Какие уровни подходят для каких изменений, описано в [skill/reference/api-matrix.md](../skill/reference/api-matrix.md).

Ссылка на образы не нужна. `adbm setup` строит план: [`sdkmanager`](https://developer.android.com/tools/sdkmanager) скачивает недостающие образы из
репозитория Google в `$ANDROID_HOME/system-images/`, [`avdmanager`](https://developer.android.com/tools/avdmanager) создаёт [AVD](https://developer.android.com/studio/run/emulator). Уровень, для которого
уже есть телефонный AVD, `setup` пропускает. AVD для Wear, TV, Automotive и планшетов не считаются. Уже скачанный образ он использует повторно. Если `image` или `profile`
не совпадают с существующим AVD, `setup` об этом пишет, а AVD не трогает: чтобы пересоздать, удали его.

Чтобы добавить уровень, допиши число в `apis` и запусти `adbm setup`. Без `--yes` он только печатает план.

## Модель субагента

```ini
[adbm-eyes]
model = haiku     # sonnet, opus, haiku, fable; пусто — модель типа агента
effort = low      # low, medium, high, xhigh, max; пусто — обычный effort
```

По умолчанию [субагент](https://code.claude.com/docs/en/sub-agents) `adbm-eyes` работает на `haiku` с effort `low`.

Сильная модель здесь не нужна: главное решают детерминированные проверки. `adbm diff` без модели
находит изменённые пары, область и процент изменения, отдельно сравнивает статус-бар. Модель только
объясняет результат: пишет, что именно сломалось, и отмечает пары с проблемой. Если модель ошибётся,
изменённая пара всё равно останется на борде, и человек её увидит.

На [примере прогона](example.ru.md) `haiku` и `sonnet` дали одинаковый вердикт: 6 PROBLEM и 2 EXPECTED.
При effort `high` субагент потратил больше токенов и пропустил светлый навбар.

Эти настройки модели и effort действуют в Claude Code. Скилл передаёт их, если инструмент Agent
поддерживает эти параметры. Codex и другие клиенты используют свои модели и инструменты запуска.
См. [инструкцию для субагента](../skill/reference/visual-check.md#the-adbm-eyes-subagent).

## Хук-ограждение

[Хук Claude Code](https://code.claude.com/docs/en/hooks) `skill/hooks/adbm-guard.py` запрещает `Read` полноразмерного кадра и сырого дампа UI. Так агент
не потратит ~3350 токенов на один скриншот случайно.

- **Плагин** ставит хук сам (`skill/hooks/hooks.json`).
- **Установка симлинком:** `adbm setup --hook --yes` дописывает хук в `hooks.PreToolUse` файла
  `~/.claude/settings.json` (или `$CLAUDE_CONFIG_DIR`, если задан). Остальные настройки и права файла
  сохраняются. Прежний файл копируется в `settings.json.adbm-backup` рядом с настоящим файлом
  (если это симлинк — рядом с его целью).

Хук меняет Claude Code во всех проектах, поэтому ставится только с `--yes` после согласия человека.
До тех пор `adbm doctor` показывает его как предупреждение (`!`). Руками блок такой:

```json
"hooks": {
  "PreToolUse": [{ "matcher": "Read", "hooks": [{ "type": "command",
    "command": "f=~/.claude/skills/adbm/hooks/adbm-guard.py; [ -f \"$f\" ] || exit 0; exec python3 \"$f\"" }] }]
}
```

## Агент adbm-eyes

`adbm setup --agent --yes` ставит симлинк `~/.claude/agents/adbm-eyes.md` на `skill/agents/adbm-eyes.md`.
Если на его месте лежит обычный файл, он копируется в `adbm-eyes.md.adbm-backup`. Плагин ставит агента сам.
Если агент не установлен, Claude Code может запустить `general-purpose` с теми же инструкциями.
Codex и другие клиенты используют [общие инструкции для агента](../skill/agents/adbm-eyes.md) без этой установки.
