# ADBM — Android Debug Bridge Matrix

[English](README.md)

Claude Code skill и CLI `adbm`: агент работает с Android-устройством и эмуляторами через adb
и тратит на это мало токенов. Агент вызывает команды `adbm` вместо сырого `adb`.

- **Управление устройством.** Агент запускает и останавливает приложение, ходит по экрану,
  вводит текст (в том числе кириллицу), читает logcat, выдаёт разрешения, копирует файлы.
- **Несколько API сразу.** Агент поднимает эмуляторы нужных версий Android, ставит APK
  и прогоняет Maestro flow на всех API параллельно, с матрицей тем и навигации.
- **Скриншоты и видео.** Агент снимает кадры в папку прогона, берёт уменьшенный кадр или фрагмент, пишет видео.
- **Проверка изменений.** Агент ставит сборки «до» и «после» и считает пиксельный дифф.
  Затем `adbm` собирает HTML-борд и PNG-коллаж «до | после», а субагент пишет вердикт.

Кадр 1080×2400 стоит модели ~3350 токенов, поэтому картинки в контекст агента не идут:

- **по экрану агент ходит по тексту** — `adbm ui` сжимает дерево UI в 10–20 раз, `adbm tap "Закрыть"`;
- **«изменилось ли» считает Python** — `adbm diff` даёт процент и область, для кадров из `adbm shot` — ещё и сдвиги элементов;
- **кадры смотрит субагент** на более дешёвой модели и возвращает до 10 строк;
- **если без картинки никак** — `adbm look` отдаёт кадр 540 px (~860 токенов) или фрагмент.

## Как это работает

Пример — реальный прогон в приложении MyPassBox. В нём сменили тему по умолчанию: была «Системная»,
стала «Тёмная». Агент проверил три экрана на API 33 и 35 при светлой и тёмной системной теме.

1. **Сборки.** `adbm install` ставит сборку «до» на все эмуляторы сразу, позже — сборку «после».
2. **Сценарий.** `adbm run` прогоняет один Maestro flow на всех API параллельно, в каждой ячейке
   матрицы `theme=light,dark`. Кадры ложатся в папку прогона, в контекст агента они не попадают.
3. **Дифф.** `adbm diff` сравнивает пары «до | после» по пикселям и пишет одну строку на пару:

   ```
   api33/dark/2-settings: 2.5% @45,483-1035,582
   api35/dark/2-settings: ≈ api33: the same change
   api33/light/1-empty-list: 94.4% @0,96-1080,2274 · status bar differs
   api35/light/1-empty-list: ≈ api33: the same change
   …
   pairs 12, changed 8 (4 same as another API), unchanged 4 · diff images: diff/
   ```

   Неизменённые пары дальше никто не смотрит. Значок `≈` значит, что на другом API пара изменилась так же.
   Для небольшого изменения дифф вырезает кроп: «до» сверху, «после» снизу. Здесь это переключатель темы:

   ![Кроп диффа: переключатель темы до и после](docs/img/diff-crop.png)

   Статус-бар дифф сравнивает отдельно. На этом кропе видна ошибка: в «после» тёмные часы и иконки на тёмном фоне.

   ![Кроп статус-бара до и после](docs/img/diff-statusbar.png)

4. **Вердикт.** Субагент `adbm-eyes` смотрит коллаж и кропы по чек-листу задачи. На каждую изменённую пару
   он пишет вердикт: EXPECTED — так задумано, PROBLEM — дефект, REVIEW — нужен взгляд человека.
   Основной агент получает до 10 строк текста и не открывает ни одной картинки.
5. **Борд.** `adbm board` собирает HTML-страницу: итог, вердикты, пары кадров с процентом изменения,
   фильтр по API и режим «changed only».

![Борд прогона: итог, вердикты и пара с PROBLEM](docs/img/board.png)

Коллаж `00-summary.png` собирает все изменённые пары на одной картинке. Его смотрит субагент, а человеку
он нужен для быстрого взгляда:

![Коллаж до и после](docs/img/summary.png)

Итог прогона: тёмная тема по умолчанию работает. Но при светлой системной теме часы и иконки статус-бара
стали тёмными на тёмном фоне, а навбар остался светлым. Так на обоих API.

Команды такого прогона:

```bash
adbm new mypassbox-dark-default
adbm install before.apk --as before --api 33,35
adbm run .adbm/flows/theme-default.yaml --api 33,35 --as before --matrix theme=light,dark
adbm install after.apk --as after --api 33,35
adbm run .adbm/flows/theme-default.yaml --api 33,35 --as after --matrix theme=light,dark
adbm diff
adbm board --open
```

## Что умеет

| Команда | Что делает |
|---|---|
| `adbm doctor` | проверяет SDK, adb, emulator, Java, Maestro, Pillow, AVD и их `config.ini`, хук-ограждение, агента `adbm-eyes` и модели субагентов |
| `adbm config` | модель и effort субагентов из `~/.config/adbm/config.ini` и `.adbm/config.ini`; `--init` пишет файл со значениями по умолчанию |
| `adbm setup --api 28,33,35` | образы, AVD с 4 ГБ памяти, Maestro, Android CLI; `--hook`, `--agent` для Claude Code; без `--yes` — только план |
| `adbm devices --start 28,33,35` | поднимает эмуляторы, печатает API → serial → экран |
| `adbm prep` | анимации 0, demo mode статус-бара, тема, навигация, шрифт |
| `adbm new <slug>`, `adbm status` | начать папку прогона, показать текущий прогон и счётчики |
| `adbm install <apk> [--as before\|after]` | ставит APK на все API параллельно (по умолчанию `after`) |
| `adbm launch`, `stop`, `clear`, `uninstall`, `open <uri>`, `perm`, `log` | управление приложением: запуск, остановка, данные, deep link, разрешения, хвост logcat |
| `adbm push`, `pull`, `rotate`, `devices --stop`, `clean` | файлы, ориентация, остановка эмуляторов, удаление старых прогонов (оставляет 5; без `--yes` только печатает план) |
| `adbm flow new <slug>` | шаблон flow в `.adbm/flows/` |
| `adbm ui`, `tap`, `wait`, `assert`, `type`, `clear-field`, `key`, `swipe` | навигация по тексту дерева UI; `tap` печатает, что изменилось на экране, `--expect` ждёт следующий экран |
| `adbm shot`, `look`, `thumb`, `annotate`, `record` | кадры в папку прогона, уменьшенный кадр или фрагмент, видео |
| `adbm run <flow.yaml> --matrix …` | Maestro flow на всех API параллельно, матрица тем и навигации |
| `adbm save-flow` | ручная сессия → Maestro flow |
| `adbm diff` | пиксельный дифф (540 px, кропы, статус-бар отдельно), дифф дерева UI, `≈ apiN` для того же изменения на другом API |
| `adbm board` | HTML-борд и коллаж `00-summary.png` |

Подпапки идут в порядке осей `--matrix`. Прогон ложится в `<проект>/build/adbm/<дата-время>-<slug>/`:

```
api35/before/gestural/dark/1-peek.png
api35/after/gestural/dark/1-peek.png
diff/api35/gestural/dark/1-peek.png
logs/  notes.md  stats.json  builds.json
index.html  manifest.js  00-summary.png
```

## Установка

Нужны Android SDK, Python 3.9+ с Pillow, для сценариев и ввода не-ASCII через `adbm type` — Maestro, для видео — ffmpeg.

```bash
git clone <repo> ~/dev/adbm
ln -s ~/dev/adbm/skill ~/.claude/skills/adbm
python3 -m pip install Pillow
~/dev/adbm/skill/bin/adbm setup --hook --agent --yes   # хук-ограждение и агент adbm-eyes
~/dev/adbm/skill/bin/adbm doctor
```

CLI работает и без Claude Code: `ln -s ~/dev/adbm/skill/bin/adbm /usr/local/bin/adbm`.

**Хук-ограждение.** `skill/hooks/adbm-guard.py` запрещает `Read` полноразмерного кадра и сырого
дампа UI. Так агент не потратит ~3350 токенов на один скриншот случайно. Плагин ставит хук сам
(`skill/hooks/hooks.json`). При установке симлинком `adbm setup --hook --yes` дописывает его в
`hooks.PreToolUse` файла `~/.claude/settings.json` (или `$CLAUDE_CONFIG_DIR`, если задан). Остальные настройки
и права файла сохраняются; прежний файл копируется в `settings.json.adbm-backup` рядом с настоящим файлом
(если это симлинк — рядом с его целью). Хук меняет Claude Code во всех проектах, поэтому ставится только с `--yes`
после согласия человека. `adbm doctor` до тех пор показывает его как `missing`. Руками блок такой:

```json
"hooks": {
  "PreToolUse": [{ "matcher": "Read", "hooks": [{ "type": "command",
    "command": "f=~/.claude/skills/adbm/hooks/adbm-guard.py; [ -f \"$f\" ] || exit 0; exec python3 \"$f\"" }] }]
}
```

**Замер сессии.** `tools/measure-session.py <transcript.jsonl>` показывает, сколько сессия
Claude Code потратила на `adbm`: символы вывода по командам и прочитанные картинки.
`adbm status` даёт ту же оценку для текущего прогона из `stats.json`.

## Модель субагента

Субагент `adbm-eyes` по умолчанию работает на `haiku` с effort `low`.

Сильная модель здесь не нужна: главное решают детерминированные проверки. `adbm diff` без модели
находит изменённые пары, область и процент изменения, отдельно сравнивает статус-бар. Модель только
объясняет результат: пишет, что именно сломалось, и отмечает пары с проблемой. Если модель ошибётся,
изменённая пара всё равно останется на борде, и человек её увидит.

Haiku 5.5 с этим справляется. На прогоне MyPassBox выше он поставил тот же вердикт, что `sonnet`:
6 PROBLEM и 2 EXPECTED. Вход Haiku 5.5 стоит $0,10 за 1 млн токенов, вход Sonnet 5.5 — $2.
Effort `high` в этом прогоне не помог: субагент потратил больше токенов и пропустил светлый навбар.

Если нужна другая цена или точность, поменяй модель и effort в файле настроек.
`adbm config --init` пишет его со значениями по умолчанию:

```bash
adbm config --init            # ~/.config/adbm/config.ini ($XDG_CONFIG_HOME, если задан), для всех проектов
adbm config --init --project  # .adbm/config.ini, только для этого проекта
adbm config                   # итоговые значения и откуда они взяты
```

```ini
[adbm-eyes]
model = haiku     # sonnet, opus, haiku, fable; пусто — модель типа агента
effort = low      # low, medium, high, xhigh, max; пусто — обычный effort
```

Значения из файла проекта перекрывают пользовательский файл. Перед запуском субагента скилл вызывает
`adbm config` и передаёт `model` и `effort` в инструмент Agent. Если тип `adbm-eyes` не установлен,
скилл запускает `general-purpose`, и пустой `model` там означает модель главной сессии.

Настройка работает только в Claude Code. Если ты работаешь в другом инструменте (Codex и т. п.),
перепиши под него раздел «The adbm-eyes subagent» в `skill/SKILL.md` и файл `skill/agents/adbm-eyes.md`.

## Тесты

```bash
python3 -m unittest discover tests
```

Устройство не нужно: тесты проверяют разбор дерева UI, матрицу, дифф, вердикты, `save-flow`,
хук-ограждение и замер сессии на фикстурах из реального прогона. Без Pillow тесты картинок пропускаются.

## Почему не …

- **Android CLI от Google** — journeys выполняет LLM, прогон недетерминирован. Бинарник закрытый,
  телеметрия включена по умолчанию. ADBM использует его только для `annotate`.
- **mobile-mcp и похожие MCP** — интерактивные, держат скриншоты в контексте, работают с одним устройством.
- **Roborazzi, Paparazzi, Shot** — нужны код тестов и эталоны в git. ADBM сравнивает две сборки.
- **Percy, Emerge, Applitools** — облачные и платные.

## Лицензия

MIT
