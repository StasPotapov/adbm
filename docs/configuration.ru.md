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

Команды без `--api` берут список `apis`. Им нужны все эмуляторы из списка: подними их `adbm devices --start`.
Если какого-то уровня нет, команда остановится и подскажет, что запустить. Общий список для всех проектов
можно задать в `~/.config/adbm/config.ini`: пустой `apis` в проекте его не перекрывает.

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

Haiku 5.5 с этим справляется. На прогоне из [example.ru.md](example.ru.md) он поставил тот же вердикт,
что `sonnet`: 6 PROBLEM и 2 EXPECTED. Вход Haiku 5.5 стоит $0,10 за 1 млн токенов, вход Sonnet 5.5 — $2.
Effort `high` в этом прогоне не помог: субагент потратил больше токенов и пропустил светлый навбар.

Перед запуском субагента скилл вызывает `adbm config` и передаёт `model` и `effort` в инструмент Agent.
Если тип `adbm-eyes` не установлен, скилл запускает `general-purpose`, и пустой `model` там означает
модель главной сессии.

Настройка модели работает только в Claude Code. Если ты работаешь в другом инструменте (Codex и т. п.),
перепиши под него раздел «The adbm-eyes subagent» в `skill/reference/visual-check.md` и файл `skill/agents/adbm-eyes.md`.

## Хук-ограждение

[Хук](https://code.claude.com/docs/en/hooks) `skill/hooks/adbm-guard.py` запрещает `Read` полноразмерного кадра и сырого дампа UI. Так агент
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
Без агента всё работает: скилл запускает `general-purpose` с тем же промптом, но у такого субагента
больше инструментов и стартовый контекст больше.
