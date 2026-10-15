# ADBM — Android Debug Bridge Matrix

[Русский](README.ru.md)

A Claude Code skill and the `adbm` CLI: an agent works with an Android device and emulators
over adb and spends few tokens on it. The agent calls `adbm` commands instead of raw `adb`.

- **Device control.** The agent launches and stops the app, navigates the screen,
  types text (Cyrillic included), reads logcat, grants permissions, copies files.
- **Several API levels at once.** The agent boots emulators for the Android versions you need,
  installs the APK and runs a Maestro flow on all API levels in parallel, with a theme and navigation matrix.
- **Screenshots and video.** The agent saves frames to the run folder, takes a downscaled frame or a crop, records video.
- **Change checks.** The agent installs "before" and "after" builds and computes a pixel diff.
  Then `adbm` builds an HTML board and a "before | after" PNG contact sheet, and a subagent writes the verdict.

A 1080×2400 screenshot costs a model ~3350 tokens, so screenshots never enter the agent's context:

- **the agent navigates by text** — `adbm ui` shrinks the UI tree 10–20×, `adbm tap "Close"`;
- **"did it change" is computed in Python** — `adbm diff` reports percent and area, and element shifts for frames from `adbm shot`;
- **a subagent looks at the images** on a cheap model and returns up to 10 lines;
- **when a picture is unavoidable** — `adbm look` returns a 540 px frame (~860 tokens) or a crop.

## How it works

1. **Builds.** `adbm install` installs the "before" build on all emulators at once, later the "after" build.
2. **Scenario.** `adbm run` runs one Maestro flow on all API levels in parallel, in every cell of the theme and navigation matrix.
3. **Diff.** `adbm diff` compares "before | after" pairs pixel by pixel. Nobody looks at unchanged pairs after this.
4. **Verdict.** The `adbm-eyes` subagent looks at the changed pairs and writes EXPECTED, PROBLEM or REVIEW.
5. **Board.** `adbm board` builds an HTML page with the summary, verdicts and frame pairs.

![Run board: summary, verdicts and a PROBLEM pair](docs/img/board.png)

This is the board of a real run: the app's default theme changed, and the check found an unreadable
status bar. A step-by-step walkthrough with diff lines and crops is in [docs/example.md](docs/example.md).

## Built on

ADBM does not replace these tools: it ties them together and saves the agent's tokens.

| Tool | What it does in ADBM |
|---|---|
| [Maestro](https://github.com/mobile-dev-inc/Maestro) — an open-source UI testing framework by mobile.dev, Apache 2.0 | runs scenarios: `adbm run` runs a flow on all API levels, `adbm save-flow` writes a flow from a manual session, `adbm type` types non-ASCII text through it. Flow syntax: [Maestro docs](https://docs.maestro.dev) |
| [Android SDK](https://developer.android.com/tools): adb, emulator, sdkmanager, avdmanager | device connection, emulators, image downloads |
| [Pillow](https://python-pillow.github.io) | pixel diff, crops, contact sheet |
| [ffmpeg](https://ffmpeg.org) | frames from video for `adbm record` |
| [Android CLI](https://developer.android.com/tools/agents/android-cli), optional | only `adbm annotate`: numbered elements on a screen without a UI tree |

## Install

Requires the Android SDK and Python 3.9+ with Pillow. Scenarios and non-ASCII `adbm type` need [Maestro](https://github.com/mobile-dev-inc/Maestro), video needs ffmpeg.

```bash
git clone <repo> ~/dev/adbm
ln -s ~/dev/adbm/skill ~/.claude/skills/adbm
python3 -m pip install Pillow
~/dev/adbm/skill/bin/adbm setup --hook --agent --yes   # guard hook + adbm-eyes agent
~/dev/adbm/skill/bin/adbm doctor
```

`setup --hook` changes `~/.claude/settings.json`: the hook denies the agent reading full-size frames in every
project. What exactly it changes and how to add the hook by hand is in [docs/configuration.md](docs/configuration.md).
The CLI works without Claude Code too: `ln -s ~/dev/adbm/skill/bin/adbm /usr/local/bin/adbm`.

## Common commands

| Task | Command |
|---|---|
| what is on the screen | `adbm ui` |
| tap and wait for the next screen | `adbm tap "Settings" --expect "Theme"` |
| boot the project's emulators | `adbm devices --start` |
| install a build | `adbm install app.apk --as before` |
| run a scenario over a matrix | `adbm run .adbm/flows/x.yaml --matrix theme=light,dark` |
| compare and show | `adbm diff`, then `adbm board --open` |
| app logs | `adbm log`, `adbm log --crash` |
| check the environment | `adbm doctor` |

## Documentation

| File | What is in it |
|---|---|
| [docs/example.md](docs/example.md) | a real run step by step: commands, diff lines, crops, contact sheet, result |
| [docs/configuration.md](docs/configuration.md) | `config.ini`: API levels, subagent model and effort; the guard hook and the `adbm-eyes` agent |
| [docs/commands.md](docs/commands.md) | all commands, the run folder layout, measuring a session's tokens |
| [docs/alternatives.md](docs/alternatives.md) | similar tools: what they do and how ADBM differs |
| [skill/SKILL.md](skill/SKILL.md), [skill/reference/](skill/reference/) | instructions for the agent |

## Tests

```bash
python3 -m unittest discover tests
```

No device is needed: the tests cover the UI tree parser, the matrix, the diff, verdicts, `save-flow`, settings,
the guard hook and the session measurement on fixtures from a real run. Without Pillow the image tests are skipped.

## License

MIT
