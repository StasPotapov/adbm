# Команды

[English](commands.md) · [README](../README.ru.md)

У каждой команды есть справка: `adbm <команда> -h`. Команды для нескольких устройств принимают
`--api 28,33,35`. Без `--api` они берут уровни из настроек проекта (см. [configuration.ru.md](configuration.ru.md)).

| Команда | Что делает |
|---|---|
| `adbm doctor` | проверяет SDK, adb, emulator, Java, Maestro, Pillow, Android CLI и mobilecli (необязательные), AVD и их `config.ini`, хук-ограждение, агента `adbm-eyes` и настройки |
| `adbm config` | настройки из `~/.config/adbm/config.ini` и `.adbm/config.ini`: модель и effort субагента, уровни API; `--set devices.apis=28,33,35 --project` записывает значение |
| `adbm setup [--api 28,33,35]` | образы, AVD с 4 ГБ памяти, Maestro, Android CLI, mobilecli; `--hook`, `--agent` для Claude Code; без `--yes` — только план |
| `adbm devices --start [28,33,35]` | поднимает эмуляторы (без значения — из `[devices] apis`), печатает API → serial → экран |
| `adbm prep` | анимации 0, demo mode статус-бара, тема, навигация, шрифт |
| `adbm new <slug>`, `adbm status [<прогон>] [--json]` | начать папку прогона; токены и экономия по всем прогонам проекта, `<прогон>` — один прогон с вызовами по командам |
| `adbm install <apk> [--as before\|after]` | ставит APK на все API параллельно (по умолчанию `after`) |
| `adbm launch`, `stop`, `clear`, `uninstall`, `open <uri>`, `perm`, `log` | управление приложением: запуск, остановка, данные, deep link, разрешения, хвост [logcat](https://developer.android.com/tools/logcat) |
| `adbm location <широта,долгота>`, `location clear`, `location` | подмена GPS на всех заданных API; без аргументов показывает позицию. API 31+ (эмулятор или телефон): тестовые провайдеры `gps` и `network`, позицию раз в секунду ставит цикл на устройстве, приложения видят её как mock; `clear` их убирает и возвращает настройку геолокации и appop mock_location, какими они были до подмены. Эмулятор ниже API 31: консоль эмулятора (`geo fix`), настоящая позиция GPS; `clear` возвращает позицию загрузки. Цикл живёт до `clear` или перезагрузки. Проверено на эмуляторах API 28, 33, 35 и на Pixel с API 37. Отрицательная широта — после `--`, флаги — до него: `adbm location --api 35 -- -33.86,151.21` |
| `adbm clipboard ["<текст>"]` | буфер обмена устройства: без текста читает, с текстом записывает; нужен [mobilecli](https://github.com/mobile-next/mobilecli). На Android 13+ закрывает плашку «скопировано», чтобы она не попала в кадры |
| `adbm crashes [--app <pkg>] [--since 10-22 18:00] [--until 10-22] [-n 20]`, `adbm crashes <id> [--lines 60] [--full]` | история падений, новые сверху, можно за промежуток времени (время устройства или `12h`, `2d` назад): падения Java и native из буфера crash в logcat и из `dumpsys dropbox`, ANR — только из dropbox; dropbox хранит их и после перезагрузки. С id — текст одного падения: 60 строк без дампа регистров native, `--full` — целиком |
| `adbm push`, `pull`, `rotate`, `devices --stop`, `clean` | файлы, ориентация, остановка эмуляторов, удаление старых прогонов (оставляет 5; без `--yes` только печатает план) |
| `adbm flow new <slug>` | шаблон flow в `.adbm/flows/` |
| `adbm ui`, `tap`, `wait`, `assert`, `type`, `clear-field`, `key`, `swipe` | навигация по тексту дерева UI; `tap` печатает, что изменилось на экране, `--expect` ждёт следующий экран |
| `adbm batch '<шаг>' '<шаг>' … [--ui] [--keep-going]` | несколько действий за один вызов, например форма: каждый шаг — команда в кавычках, одна из `ui`, `tap`, `type`, `clear-field`, `key`, `swipe`, `wait`, `assert`, `launch`, `stop`, `clear`, `open`, `perm`, `rotate`, `clipboard`, `location`; шаг без `--api`/`--serial` идёт на устройство батча; все шаги проверяются до первого действия; батч останавливается на первой ошибке, `--keep-going` выполняет остальные шаги; `--ui` печатает экран после последнего выполненного шага, и после остановки тоже |
| `adbm shot`, `look`, `thumb`, `annotate`, `record` | кадры в папку прогона, уменьшенный кадр или фрагмент, видео |
| `adbm run <flow.yaml> --matrix …` | [Maestro flow](https://docs.maestro.dev) на всех API параллельно, матрица тем и навигации |
| `adbm save-flow` | ручная сессия → Maestro flow |
| `adbm diff` | пиксельный дифф (540 px, кропы, статус-бар отдельно), дифф дерева UI, `≈ apiN` для того же изменения на другом API |
| `adbm board` | HTML-борд и коллаж `00-summary.png`; с одной сборкой (без «before») — просто кадры, без «до/после» |

## Папка прогона

Прогон ложится в `<проект>/build/adbm/<дата-время>-<slug>/`. Подпапки идут в порядке осей `--matrix`:

```
api35/before/gestural/dark/1-peek.png
api35/after/gestural/dark/1-peek.png
diff/api35/gestural/dark/1-peek.png
logs/  notes.md  stats.json  builds.json
index.html  manifest.js  00-summary.png
```

`./gradlew clean` может удалить `build/adbm` вместе с `build/`: задача `clean` из шаблона Android удаляет корневую папку `build`. Нужный прогон скопируй в другое место.

Вне прогона `shot` и `record` пишут кадры в кэш проекта `~/.cache/adbm/projects/` (`$ADBM_CACHE/projects/`, если переменная задана). Такие кадры `diff` и `board` не видят.

## Замер токенов

`adbm status` выводит все прогоны проекта и итог: вызовы, токены, которые `adbm` положил в контекст агента
(текст — символы / 4, картинки — по размеру), и сэкономленные токены. `adbm status <прогон>` показывает один прогон
подробно, с вызовами и токенами по командам. `<прогон>` — полное имя папки, slug или часть имени.
`saved` — грубая оценка: она считает, что без `adbm` каждый `ui` и `tap` был бы скриншотом 1080×2400
(~3350 токенов), а каждая картинка `look` — полным кадром. Шаги `adbm batch` считаются своими командами: `tap` внутри батча — это `tap`. Вызовы по командам считаются с версии 0.2.1:
у старых прогонов в этой колонке `—`.

Счётчики лежат в папке прогона. Команда вне прогона или позже 12 часов после последней команды прогона
попадает в кэш проекта, и `adbm status` показывает её строкой «outside runs». Прогоны, которые удалил `adbm clean`
или `gradle clean` (он удаляет `build/`), в итог больше не входят. `--json` выводит то же в JSON.

`adbm` считает только свой вывод. Чтение файлов через `Read`, логи сборки и текст самого агента в него не входят.
Целую сессию Claude Code считает `tools/measure-session.py <transcript.jsonl>`: символы вывода по командам
и прочитанные картинки.
