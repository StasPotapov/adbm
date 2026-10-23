# ADBM — Android Debug Bridge Matrix

[Русский](README.ru.md)

A [Claude Code](https://code.claude.com/docs/en/overview) [skill](https://code.claude.com/docs/en/skills) and the `adbm` CLI: an agent works with an Android device and [emulators](https://developer.android.com/studio/run/emulator)
over [adb](https://developer.android.com/tools/adb) and spends few tokens on it. The agent calls `adbm` commands instead of raw `adb`.

## Why

The agent checks the app, and you only look at the result.

- **Easier for the agent.** One `adbm` command replaces a chain of `adb` calls. The agent saves tokens at every step:
  navigation, screenshots and checks. So it works faster and costs less.
- **Fully automated.** The agent boots the emulators, installs the builds, runs the scenario and compares the frames.
- **Easier for you to check.** You open one board and see only what changed, with a verdict
  for each frame. In a minute you know whether everything is fine.

## What it does

- **Device control.** The agent launches and stops the app, navigates the screen,
  types text (Cyrillic included), reads [logcat](https://developer.android.com/tools/logcat), grants permissions, copies files.
- **Several API levels at once.** The agent boots emulators for the Android versions you need,
  installs the APK and runs a [Maestro flow](https://docs.maestro.dev) on all API levels in parallel, with a theme and navigation matrix.
- **Screenshots and video.** The agent saves frames to the run folder, takes a downscaled frame or a crop, records video.
- **Change checks.** The agent installs "before" and "after" builds and computes a pixel diff.
  Then `adbm` builds an HTML board and a "before | after" PNG contact sheet, and a [subagent](https://code.claude.com/docs/en/sub-agents) writes the verdict.

A 1080×2400 screenshot costs a model ~3350 tokens, so screenshots never enter the agent's context:

- **the agent navigates by text** — `adbm ui` shrinks the UI tree 10–20×, `adbm tap "Close"`;
- **"did it change" is computed in Python** — `adbm diff` reports percent and area, and element shifts for frames from `adbm shot`;
- **a subagent looks at the images** on a cheap model and returns up to 10 lines;
- **when a picture is unavoidable** — `adbm look` returns a 540 px frame (~860 tokens) or a crop.

`adbm status` shows what this cost. Without arguments it lists every run of the project: calls, tokens `adbm` put
into the agent's context and tokens saved. `adbm status <run>` shows one run with calls and tokens per command.

```
  run                        when               calls    tokens  images      saved
  20261015-101210-insets     2026-10-15 10:12      64     2,310       1     71,950
* 20261016-155635-sheet      2026-10-16 15:56      96     3,760       1    248,423
  total                                           160     6,070       2    320,373
```

`saved` is a rough estimate: every `ui` and `tap` counts as a 1080×2400 screenshot it replaced. `adbm` counts only
its own output, not files the agent read or its own text. Counters live in each run's `stats.json`, so deleting old
runs (`adbm clean`) removes them from the total. Details: [docs/commands.md](docs/commands.md#measuring-tokens).

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

| Tool | License | What it does in ADBM |
|---|---|---|
| [Maestro](https://github.com/mobile-dev-inc/Maestro) — a UI testing framework by mobile.dev | Apache 2.0, open source | runs scenarios: `adbm run` runs a flow on all API levels, `adbm save-flow` writes a flow from a manual session, `adbm type` types non-ASCII text through it when mobilecli is not installed. Flow syntax: [Maestro docs](https://docs.maestro.dev) |
| [Android SDK](https://developer.android.com/tools): adb, emulator, sdkmanager, avdmanager | Google's [Android SDK License Agreement](https://developer.android.com/studio/terms); open-source parts of the SDK keep their own licenses | device connection, emulators, image downloads |
| [Pillow](https://python-pillow.github.io) | MIT-CMU, open source | pixel diff, crops, contact sheet |
| [FFmpeg](https://ffmpeg.org) | LGPL 2.1+, open source; a build with `--enable-gpl` is GPL 2+ | frames from video for `adbm record` |
| [Android CLI](https://developer.android.com/tools/agents/android-cli), optional | a closed Google binary, no published license; collects usage data, `adbm` turns that off with `--no-metrics` | needed for screens without a UI tree: games, Canvas, WebView without accessibility. `adbm annotate` draws numbers of the found elements on a frame, `adbm tap '#7'` taps by number. Without Android CLI everything else works, and on such a screen the agent taps by coordinates from an `adbm look` frame. When the agent meets such a screen, it offers to install Android CLI and installs it only after you agree: `adbm setup --android-cli --yes` |
| [mobilecli](https://github.com/mobile-next/mobilecli) by Mobile Next, optional | [FSL-1.1-ALv2](https://github.com/mobile-next/mobilecli/blob/main/LICENSE): the source is open, but it is not an OSI license — it forbids a competing commercial product built on its code; each release becomes Apache 2.0 two years later. `adbm` does not ship it, it calls the copy you installed. No telemetry found in its code (checked 23.10.2026, version 1.0.21) | the device clipboard: `adbm clipboard` reads and writes it, `adbm type` pastes non-ASCII text through it in 2–3 s instead of ~8 s through Maestro. Without mobilecli everything else works. It is installed only after you agree: `adbm setup --mobilecli --yes` (npm) |

## Install

Requires the Android SDK and Python 3.9+ with Pillow. Scenarios need [Maestro](https://github.com/mobile-dev-inc/Maestro), and so does non-ASCII `adbm type` without mobilecli; video needs ffmpeg.

Platforms: macOS is tested. Linux should work: it needs `/dev/kvm` for the emulator. Windows is not supported; WSL is not tested.

There are two ways to install. Pick one: with both, the skill and the hook load twice.

**As a Claude Code plugin.** One step installs the skill, the `adbm-eyes` agent and the guard hook.
The skill is then called `adbm:adbm`, the agent `adbm:adbm-eyes`.

```
/plugin marketplace add StasPotapov/adbm
/plugin install adbm@adbm
```

Then install Pillow (see below) and run `adbm doctor` through the agent: ask it to check the environment.
The plugin does not put `adbm` on the terminal's PATH; for terminal use, clone the repository as below.
To get a new version: `/plugin marketplace update adbm`, then `/plugin update adbm@adbm`.

**From a clone.** The skill is a symlink, the hook and the agent are added by `adbm setup`:

```bash
git clone https://github.com/StasPotapov/adbm.git ~/dev/adbm
mkdir -p ~/.claude/skills
ln -s ~/dev/adbm/skill ~/.claude/skills/adbm
python3 -m pip install Pillow   # Homebrew Python: brew install pillow; Debian/Ubuntu: sudo apt install python3-pil
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
| several actions in one call | `adbm batch 'tap Email' 'type a@b.c' 'tap Next' --ui` |
| boot the project's emulators | `adbm devices --start` |
| install a build | `adbm install app.apk --as before` |
| run a scenario over a matrix | `adbm run .adbm/flows/x.yaml --matrix theme=light,dark` |
| compare and show | `adbm diff`, then `adbm board --open` |
| app logs, crashes | `adbm log`, `adbm log --crash`, `adbm crashes` |
| tokens spent and saved | `adbm status`, `adbm status <run>` |
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
