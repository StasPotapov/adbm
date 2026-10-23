---
name: adbm
description: "Drives an Android device or emulator for the agent instead of raw adb, at a fraction of the tokens: reads the screen as compact text, taps by text, types, swipes, presses keys, installs, launches and stops apps, reads logcat and crashes, opens deep links, grants permissions, reads and writes the clipboard, copies files, takes screenshots. On top of that it checks how the app looks: boots emulators for the needed API levels, runs Maestro flows on them in parallel with a theme and navigation matrix, compares \"before\" and \"after\" builds on an HTML board, and a subagent writes the verdict. - Any adb or device task: \"launch the app on the emulator\", \"what is on the screen\", \"tap Settings\", \"install the APK\", \"show the crash log\", \"grant the permission\", \"open the deep link\", \"take a screenshot\". Checks: \"check it on the emulator\", \"before/after screenshots\", \"how it looks on API 28/33/35\", \"run the flow in dark theme\", \"check the insets / bottom sheet change\"."
argument-hint: "<what to do or check> [--api 28,33,35]"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
---

# ADBM — Android Debug Bridge Matrix

ADBM is how you work with an Android device or emulator. Use it for every device task, not raw `adb`.
It has two layers:

- **Device control.** What you would do with `adb`: read the screen, tap, type, run apps, read logs,
  deep links, permissions, files, screenshots. One command per action, no setup and no run folder.
- **Checks.** Built on device control: emulators by API level, Maestro flows in parallel, "before" and
  "after" builds, a diff, an HTML board and the `adbm-eyes` verdict. For "how does it look" and "what changed".

Start with device control. Go to "Visual check" only when the task needs frames to compare,
several API levels or a theme and navigation matrix.

The CLI is `bin/adbm` of this skill: `ADBM="${CLAUDE_SKILL_DIR}/bin/adbm"`. If the variable is not
substituted, take the folder from the "Base directory for this skill" line. Run commands from the
project root: runs go to `<project>/build/adbm/<date>-<slug>/`. The project is the git root of the
current folder; `ADBM_PROJECT=<path>` overrides it. Help: `"$ADBM" <command> -h`. Commands below
omit the prefix: run `"$ADBM" <command>`, and set the variable in every Bash call (it does not persist).

## Device control

| The person asks | Run |
|---|---|
| what is on the screen | `ui --api 35` (`--find <text>` to narrow) |
| tap, open a screen | `tap "<text>" --expect "<text on the next screen>"` |
| type into a field, clear it | `type "<text>"`, `clear-field`; non-Latin — see "Limitations" |
| read or set the clipboard, check a "Copy" button | `clipboard` reads, `clipboard "<text>"` writes; needs mobilecli (`doctor`) |
| back, home, enter, keyboard, scroll, orientation | `key back` (`home`, `enter`, `hide-keyboard`, …), `swipe up`, `rotate landscape` |
| wait for a screen, is a text there | `wait "<text>"`, `assert "<text>"`: exit code 0 or 1 |
| several actions in a row: a form, a known path | `batch 'tap Email' 'type a@b.c' 'tap Next --expect Done' --ui`: one call, stops at the first failure (`--keep-going` — run the rest); steps: `ui tap type clear-field key swipe wait assert launch stop clear open perm rotate clipboard` |
| install, launch, stop, clear data | `install <apk>`, `launch <pkg>`, `stop`, `clear`, `uninstall` |
| logs, crash | `log` (the app's process), `log --crash`, `log --grep <re>`; crash history with ANR and native, also before a reboot — `crashes [--app <pkg>]`, one crash — `crashes <id>` |
| deep link, permission, file | `open <uri>`, `perm <pkg> grant CAMERA`, `push`, `pull` |
| a screenshot | for you to see — `look` (~860 tokens); for the person — `shot <name>`, give the path, do not read it |
| which devices, boot an emulator | `devices`, `devices --start` (the project's API levels) or `--start 33,35`, `devices --stop 33` |
| device theme, navigation mode, font scale, locale | `prep --theme dark`, `--nav gestural`, `--font-scale 1.3`, `--locale ru-RU --app <pkg>` |
| no `adbm` command for it | raw `adb -s <serial>` from `reference/adb.md` |
| how it looks, before/after, several API levels, themes | "Visual check" below |

A single action needs no `doctor`, `new`, `diff` or `board`. Only `new` and `run` start a run; outside one
`adbm` writes to `~/.cache/adbm/`, and `shot`/`record` frames there are unseen by `diff` and `board`.
`doctor` only if something does not start. Address devices by `--api N`, a physical device by `--serial`.

## Token economy

A 1080×2400 image costs ~3350 tokens, a line of `adbm ui` ~15.

1. **Navigate by text.** `ui`, then `tap "<text>"`. `tap` prints what appeared, went away and switches that flipped;
   `--expect` confirms the next screen in one line. Do not call `ui` after every tap.
   A tap by `x,y` or `#N` prints no change — add `--expect`. `[N]` from `ui` works only on that screen.
   Steps you already know (fill a form, go down a known path) — one `batch` instead of a call per action.
   Text that looks like `x,y`, `#N` or `[N]` (a price "1,500"): `tap "text:1,500"`.
2. **Do not open frames.** `shot` and `run` save frames to the run, not to the context. Never `Read` a file
   from `api*/`. `adbm diff` decides what changed; the `adbm-eyes` subagent looks at images.
3. **One picture when nothing else helps:** `look` (540 px, ~860 tokens), `--small` (~380), `--crop` (up to
   ~1850). Screen coordinate = image coordinate / `scale` from the output. Over 3 `look` per task — stop.
4. **Logs:** read only on failure and only the part you need (`tail`, `grep`).

`adbm status` estimates what `adbm` put into the context and what it saved, per run of the project; `status <run>` — one run. If the guard hook is installed (plugin, or
`settings.json` per `docs/configuration.md`), it denies `Read` of a frame or a raw XML dump: do what the denial says.

## Visual check

1. **Environment.** `doctor`; rows that block the task — show the fix and ask; `setup` without `--yes` only plans.
   `setup --hook` / `--agent` change the person's Claude Code settings: run them with `--yes` only after a clear yes.
2. **API levels.** `config` shows the project's set: `devices  apis=…`; commands without `--api` use it.
   `apis=-` (first check in the project): find `minSdk`/`targetSdk` in `build.gradle*`, offer a set with
   reasons from `reference/api-matrix.md` and wait for the answer. Then `config --set devices.apis=<list> --project`
   and `setup`: its plan downloads only the missing system images and AVDs. A change that needs other
   levels (insets, theme, permissions) — offer them and pass `--api` for this check only.
3. **Run and builds.** `new <slug>`. Comparing builds: `install <before.apk> --as before --api …`, "before" frames,
   then `install <after.apk>` and all "after" frames. One build as installed: frames only, `diff` says `after only`.
4. **Frames.** By hand for 1–2 frames on 1–2 API levels: `prep`, `launch`, `tap`, `shot <name>`.
   A Maestro flow when the path is longer than 3–4 steps, for a theme/navigation/font matrix, for
   three API levels or when the check repeats: `flow new <slug>`, then `run .adbm/flows/<slug>.yaml --api 35`,
   then all API levels with `--matrix`. Details, axes, video: `reference/workflow.md`; writing flows:
   `reference/flows.md`; a failed or hung `run`: `reference/troubleshooting.md`.
5. **Diff and board.** `diff`, then `board`. Then start `adbm-eyes` (next section).
6. **Report.** `<run>/index.html`; counts of expected/problem/review/unchanged; what broke where; 1–3 frames.

**Which build a frame belongs to:** `--as before|after` on `shot`/`run`; without it — the build of the
last `install` (the run's `.as` file); with no install — `after`.

## The adbm-eyes subagent

Use the agent type `adbm-eyes` (`adbm:adbm-eyes` when ADBM is a plugin) if the Agent tool lists it.
Otherwise: Agent with `subagent_type: general-purpose` and as the prompt the content
of `agents/adbm-eyes.md` of this skill without frontmatter.

In both cases model and effort come from the person's settings: run `adbm config` and take
the `adbm-eyes` line. Pass its `model` and `effort` to the Agent tool; do not pass a value shown as `-`.
The person sets them in `~/.config/adbm/config.ini` or the project's `.adbm/config.ini`.

Append to the prompt:

```
Task: <what was changed and what should come out>
Checklist: <2–6 items>
Run: <absolute path to the run folder>
ADBM: <absolute path to the adbm CLI>
Changed pairs:
<adbm diff output>
```

It writes the verdict to `<run>/notes.md` and returns up to 10 lines. Then `board` again (`--open` to show it).

## References

| File | When to read |
|---|---|
| `reference/workflow.md` | by-hand frames, flows and matrix axes, video, the check in detail |
| `reference/troubleshooting.md` | `run` failed or hung, black or empty frames, device problems |
| `reference/flows.md` | writing and fixing a Maestro flow |
| `reference/api-matrix.md` | which API levels and axes to offer for a change |
| `reference/setup.md` | SDK, AVDs, Maestro, Android CLI, mobilecli, a "before" build in a worktree |
| `reference/adb.md` | raw adb for what `adbm` does not do |

## Limitations

- **Non-Latin text:** `input text` cannot type it. With mobilecli `adbm type` pastes it through the clipboard
  (~2–3 s; the clipboard is replaced) and checks that the focused field got it, without it — Maestro `inputText` (~8–10 s). If `type` of such text
  is slow and mobilecli is missing, offer `setup --mobilecli --yes` and run it after a clear yes.
  In a flow write `inputText` as usual.
- **mobilecli** (`clipboard`, fast non-Latin `type`): Android 10+ lets only the foreground app read the clipboard;
  mobilecli reads it through an on-device agent with shell rights. That agent blocks `uiautomator dump`. `adbm` stops
  it after every call; if `ui` fails after mobilecli ran from elsewhere — `reference/troubleshooting.md`.
- **`FLAG_SECURE`** (banks, password managers): empty or black frames — see `reference/troubleshooting.md`.
- API 28: no gesture navigation (`nav=gestural` cells are skipped); dark theme does not reach its system UI.
- A physical device is picked only when no emulator has that API level: address it with `--serial`.
