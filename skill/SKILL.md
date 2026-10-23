---
name: adbm
description: "Drives an Android device or emulator for the agent instead of raw adb, at a fraction of the tokens: reads the screen as compact text, taps by text, types (Cyrillic too), swipes, presses keys, runs several actions in one call, installs, launches and stops apps, reads logcat and the crash history (ANR, native, before a reboot), opens deep links, grants permissions, fakes the GPS location, reads and writes the clipboard, copies files, takes screenshots. On top of that it checks how the app looks: boots emulators for the needed API levels, runs Maestro flows on them in parallel with a theme and navigation matrix, shows the screens on an HTML board, compares \"before\" and \"after\" builds when a change needs checking, and a subagent writes the verdict. - Any adb or device task: \"launch the app on the emulator\", \"what is on the screen\", \"tap Settings\", \"install the APK\", \"show the crash log\", \"why did it crash yesterday\", \"grant the permission\", \"open the deep link\", \"set the location to Moscow\", \"what is in the clipboard\", \"fill in the form\", \"take a screenshot\". Checks: \"check it on the emulator\", \"show me the screens\", \"before/after screenshots\", \"how it looks on API 28/33/35\", \"run the flow in dark theme\", \"check the insets / bottom sheet change\"."
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
- **Checks.** Built on device control: emulators by API level, Maestro flows in parallel, frames on an HTML
  board, the `adbm-eyes` verdict. Screens of one build for "how does it look"; "before" and "after" builds
  with a diff only for "what did the change do".

Start with device control. Go to "Visual check" (`reference/visual-check.md`) when the person wants to see
screens on a board, several API levels, a theme and navigation matrix, or what a change did.

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
| fake GPS: maps, delivery, city choice | `location 55.7558,37.6173`, `location clear`, `location` shows it; a negative latitude after `--`, flags before it |
| read or set the clipboard, check a "Copy" button | `clipboard` reads, `clipboard "<text>"` writes; needs mobilecli (`doctor`) |
| back, home, enter, keyboard, scroll, orientation | `key back` (`home`, `enter`, `hide-keyboard`, …), `swipe up`, `rotate landscape` |
| wait for a screen, is a text there | `wait "<text>"`, `assert "<text>"`: exit code 0 or 1 |
| several actions in a row: a form, a known path | `batch 'tap Email' 'type a@b.c' 'tap "Sign in" --expect Done' --ui`: one call, each step in its own quotes, stops at the first failure (`--keep-going` — run the rest); steps: `ui tap type clear-field key swipe wait assert launch stop clear open perm rotate clipboard location` |
| install, launch, stop, clear data | `install <apk>`, `launch <pkg>`, `stop`, `clear`, `uninstall` |
| logs, crash | `log` (the app's process), `log --crash`, `log --grep <re>`; crash history with ANR and native, also before a reboot — `crashes [--app <pkg>]`, one crash — `crashes <id>` |
| deep link, permission, file | `open <uri>`, `perm <pkg> grant CAMERA`, `push`, `pull` |
| a screenshot | for you to see — `look` (~860 tokens); for the person — `shot <name>`, give the path, do not read it |
| which devices, boot an emulator | `devices`, `devices --start` (the project's API levels) or `--start 33,35`, `devices --stop 33` |
| device theme, navigation mode, font scale, locale | `prep --theme dark`, `--nav gestural`, `--font-scale 1.3`, `--locale ru-RU --app <pkg>` |
| no `adbm` command for it | raw `adb -s <serial>` from `reference/adb.md` |
| screens on a page for the person, how it looks on API 33/35, themes | `reference/visual-check.md`, "Screens" |
| what a change did: a fix, a bug, before/after | `reference/visual-check.md`, "Before/after" |

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

For "how does it look", screens on a board, several API levels, a theme or navigation matrix, and for
"what did the change do": read `reference/visual-check.md` first. Screens of one build are the default;
"before" and "after" builds only when the task is about a change. It has the steps (`doctor`, API levels,
`new`, frames, `diff`, `board`) and how to start the `adbm-eyes` subagent that looks at the frames.

## References

| File | When to read |
|---|---|
| `reference/visual-check.md` | a visual check: screens or before/after, steps, the `adbm-eyes` subagent |
| `reference/workflow.md` | by-hand frames, flows and matrix axes, video, the check in detail |
| `reference/troubleshooting.md` | `run` failed or hung, black or empty frames, device problems |
| `reference/flows.md` | writing and fixing a Maestro flow |
| `reference/api-matrix.md` | which API levels and axes to offer for a change |
| `reference/setup.md` | SDK, AVDs, Maestro, Android CLI, mobilecli, a "before" build in a worktree |
| `reference/adb.md` | raw adb for what `adbm` does not do |

## Limitations

Details are in `<command> -h`.

- **Non-Latin text:** with mobilecli `type` pastes it through the clipboard (~2–6 s, the clipboard is replaced),
  without it — Maestro (~8–17 s). Slow and no mobilecli: offer `setup --mobilecli --yes`, run it after a clear yes.
  In a flow write `inputText` as usual.
- **mobilecli** (`clipboard`, fast non-Latin `type`): its on-device agent blocks `uiautomator dump`; `adbm` stops it
  after every call. `ui` fails after mobilecli ran from elsewhere — `reference/troubleshooting.md`.
- **`location`** on API 31+: apps see it as mock; it stays until `location clear` or a reboot — run `clear`
  when the check is over. A phone below API 31 is not supported.
- A physical device is picked only when no emulator has that API level: address it with `--serial`.
- **`FLAG_SECURE`** (banks, password managers): empty or black frames — `reference/troubleshooting.md`.
