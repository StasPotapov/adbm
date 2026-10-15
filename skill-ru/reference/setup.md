# Окружение и сборки

## Что нужно

| Что | Зачем | Как поставить |
|---|---|---|
| Android SDK: `platform-tools`, `emulator`, `cmdline-tools` | adb, эмуляторы, `sdkmanager` и `avdmanager` | Android Studio → SDK Manager → SDK Tools |
| Java 17+ | Maestro, `sdkmanager`, Gradle | `brew install openjdk@17` |
| Python 3.9+ и Pillow | сам `adbm`: коллаж, дифф, `look` | `python3 -m pip install Pillow` |
| Maestro | `adbm run` | `adbm setup --maestro --yes` (Homebrew `mobile-dev-inc/tap/maestro`) |
| ffmpeg | лист кадров в `adbm record` | `brew install ffmpeg` |
| Android CLI, необязательно | только `adbm annotate` | `adbm setup --android-cli --yes` (cask `android-cli`) |

`adbm doctor` проверяет всё это и печатает команду починки на каждую строку.
Сам `doctor` ничего не ставит.

## `adbm setup`

Без `--yes` команда печатает только план. Покажи план человеку и дождись согласия.

```bash
adbm setup --api 28,33,35            # план: образы, AVD, тюнинг
adbm setup --api 28,33,35 --yes      # выполнить
adbm setup --tune --yes              # поправить config.ini уже существующих AVD
adbm setup --maestro --android-cli --yes
```

- **Образ** — `system-images;android-N;google_apis;<abi>`: на Apple Silicon `arm64-v8a`, иначе `x86_64`.
  Образ `google_apis` даёт `adb root`, образ `playstore` — нет.
- **AVD** создаётся с именем `adbm_API_N` на профиле `pixel_8`.
- **Тюнинг** `config.ini`: `hw.ramSize=4096`, `vm.heapSize=576`, `hw.cores=4`,
  `disk.dataPartition.size=8G`, `hw.keyboard=yes`, `hw.gpu.mode=host`.
  С 2 ГБ памяти эмулятор API 35 тормозит, и Maestro ловит таймауты.
  `hw.keyboard=yes` убирает экранную клавиатуру с кадров.
- **Запущенный AVD** `--tune` пропускает: конфиг читается только при старте.

## Android CLI

Это закрытый бинарник Google, внутри JVM. Телеметрия у него включена по умолчанию.
`adbm` передаёт `--no-metrics` в каждый вызов. `android init` не запускай: он ставит свой
skill во все каталоги агентов.

`adbm annotate` вызывает `android screen capture --annotate --device <serial> -o <png>`.
Рамки строит компьютерное зрение по картинке, а не дерево UI. Затем `adbm tap '#N'`
вызывает `android screen resolve --screenshot <png> --string '#N'` и получает `x y`.
Нужен для экранов, где дерево пустое: Canvas, игры, WebView без доступности.

## Эмуляторы

```bash
adbm devices                      # API → serial → AVD → экран
adbm devices --start 28,33,35     # поднять недостающие, ждать sys.boot_completed
adbm devices --start 35 --headless
```

Лог запуска эмулятора — `~/.cache/adbm/emu-<AVD>.log`.

## Сборки «до» и «после»

«После» — текущий код: `./gradlew :app:assembleDebug`.

«До» собирай из базового коммита в отдельном worktree, чтобы не трогать рабочую копию:

```bash
BASE=$(git merge-base HEAD origin/main)       # или коммит до правки
git worktree add ../<repo>-before $BASE
(cd ../<repo>-before && ./gradlew :app:assembleDebug)
adbm install ../<repo>-before/app/build/outputs/apk/debug/app-debug.apk --as before --api 28,33,35
adbm install app/build/outputs/apk/debug/app-debug.apk --as after --api 28,33,35
git worktree remove ../<repo>-before          # после проверки
```

Если правка ещё не сделана, проще снять «до» сразу на текущем коде, а «после» — после правки.

Оба APK имеют один `applicationId`, поэтому на устройстве живёт одна версия за раз.
Порядок такой: поставить «до», снять всё «до», поставить «после», снять всё «после».
`adbm install` пишет пакет и sha1 в `builds.json` прогона, борд их показывает.
