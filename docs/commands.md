# Commands

[Русский](commands.ru.md) · [README](../README.md)

Every command has help: `adbm <command> -h`. Multi-device commands take `--api 28,33,35`.
Without `--api` they use the API levels from the project settings (see [configuration.md](configuration.md)).

| Command | What it does |
|---|---|
| `adbm doctor` | checks SDK, adb, emulator, Java, Maestro, Pillow, Android CLI and mobilecli (optional), AVDs and their `config.ini`, the guard hook, the `adbm-eyes` agent and the settings |
| `adbm config` | settings from `~/.config/adbm/config.ini` and `.adbm/config.ini`: subagent model and effort, API levels; `--set devices.apis=28,33,35 --project` writes a value |
| `adbm setup [--api 28,33,35]` | system images, AVDs with 4 GB RAM, Maestro, Android CLI, mobilecli; `--hook`, `--agent` for Claude Code; without `--yes` it only prints the plan |
| `adbm devices --start [28,33,35]` | boots emulators (without a value — from `[devices] apis`), prints API → serial → screen |
| `adbm prep` | animations off, status bar demo mode, theme, navigation mode, font scale; the first change saves the device state |
| `adbm restore` | puts the device back as it was before adbm: animations, demo mode, theme, navigation, font scale, rotation, app locales, fake GPS. `run` does it by itself at the end (`--keep` — no), `record --slow` puts the animation scales back |
| `adbm new <slug>`, `adbm status [<run>] [--json]` | start a run folder; tokens and saved tokens of every run of the project, `<run>` — one run with calls per command |
| `adbm install <apk> [--as before\|after]` | installs an APK on all API levels in parallel (`after` by default) |
| `adbm launch`, `stop`, `clear`, `uninstall`, `open <uri>`, `perm`, `log` | app control: launch, force-stop, data, deep link, permissions, [logcat](https://developer.android.com/tools/logcat) tail |
| `adbm location <lat,lon>`, `location clear`, `location` | fake GPS on all given API levels; without arguments shows the location. API 31+ (emulator or phone): test providers `gps` and `network`, the location is set every second by a loop on the device, apps see it as mock; `clear` removes them and restores the location setting and the mock_location appop as they were before. An emulator below API 31: its console (`geo fix`), a real GPS fix; `clear` moves it back to the boot location. The loop lives until `clear` or a reboot. Checked on emulators API 28, 33, 35 and on a Pixel with API 37. A negative latitude goes after `--`, flags before it: `adbm location --api 35 -- -33.86,151.21` |
| `adbm clipboard ["<text>"]` | the device clipboard: without text reads it, with text writes it; needs [mobilecli](https://github.com/mobile-next/mobilecli). On Android 13+ closes the "copied" overlay so it does not get into frames |
| `adbm crashes [--app <pkg>] [--since 10-22 18:00] [--until 10-22] [-n 20]`, `adbm crashes <id> [--lines 60] [--full]` | crash history, newest first, optionally for a time span (device time, or `12h`, `2d` ago): Java and native crashes from the logcat crash buffer and `dumpsys dropbox`, ANR only from dropbox; dropbox keeps them after a reboot. With an id — the text of one crash: 60 lines without native register dumps, `--full` — all of it |
| `adbm push`, `pull`, `rotate`, `devices --stop`, `clean` | files, orientation, stop emulators, delete old runs (keeps 5; without `--yes` only prints the plan) |
| `adbm flow new <slug>` | a flow template in `.adbm/flows/` |
| `adbm ui`, `tap`, `wait`, `assert`, `type`, `clear-field`, `key`, `swipe` | navigation by UI tree text; `tap` prints what changed on the screen, `--expect` waits for the next screen |
| `adbm batch '<step>' '<step>' … [--ui] [--keep-going]` | several actions in one call, e.g. a form: each step is a command in quotes, one of `ui`, `tap`, `type`, `clear-field`, `key`, `swipe`, `wait`, `assert`, `launch`, `stop`, `clear`, `open`, `perm`, `rotate`, `clipboard`, `location`; a step without `--api`/`--serial` runs on the batch device; every step is checked before the first one runs; the batch stops at the first failure, `--keep-going` runs the remaining steps; `--ui` prints the screen after the last step that ran, also after a stop |
| `adbm shot`, `look`, `thumb`, `annotate`, `record` | frames into the run folder, a downscaled frame or crop, video |
| `adbm run <flow.yaml> --matrix …` | a [Maestro flow](https://docs.maestro.dev) on all API levels in parallel, theme and navigation matrix |
| `adbm save-flow` | manual session → Maestro flow |
| `adbm diff` | pixel diff (540 px, crops, status bar apart), UI tree diff, `≈ apiN` for the same change on another API |
| `adbm board` | HTML board and `00-summary.png` contact sheet; with one build (no "before") — just the frames, without before/after |

## Run folder

A run is stored in `<project>/build/adbm/<date-time>-<slug>/`. Subfolders follow the order of axes in `--matrix`:

```
api35/before/gestural/dark/1-peek.png
api35/after/gestural/dark/1-peek.png
diff/api35/gestural/dark/1-peek.png
logs/  notes.md  stats.json  builds.json
index.html  manifest.js  00-summary.png
```

`./gradlew clean` can delete `build/adbm` together with `build/`: the Android template's `clean` task deletes the root `build` folder. Copy a run you want to keep elsewhere.

Outside a run `shot` and `record` write frames to the project cache `~/.cache/adbm/projects/` (`$ADBM_CACHE/projects/` if set). `diff` and `board` do not see them.

## Measuring tokens

`adbm status` lists every run of the project with a total: calls, tokens `adbm` put into the agent's context
(text as characters / 4, images by size) and saved tokens. `adbm status <run>` shows one run in detail, with calls
and tokens per command; `<run>` is the full folder name, the slug or a part of the name.
`saved` is a rough estimate: it assumes every `ui` and `tap` would otherwise be a 1080×2400 screenshot
(~3350 tokens) and every `look` image a full one. Steps of `adbm batch` count as their own commands: a `tap` in a batch is a `tap`. Calls per command are counted since 0.2.1: for older runs
the column shows `—`.

Counters live in the run folder. A command outside a run, or more than 12 hours after the run's last command,
goes to the project cache, and `adbm status` shows it as "outside runs". Runs removed by `adbm clean`
or by `gradle clean` (it deletes `build/`) are no longer counted. `--json` prints the same as JSON.

`adbm` counts only its own output. `Read` of files, build logs and the agent's own text are not in it:
`tools/measure-session.py <transcript.jsonl>` counts a whole Claude Code session — characters of output
per command and images read.
