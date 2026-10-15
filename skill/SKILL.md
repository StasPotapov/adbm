---
name: adbm
description: "Checks Android apps on emulators as an agent while saving tokens: boots emulators for the needed API levels, installs \"before\" and \"after\" builds, navigates the UI by tree text, runs Maestro flows on several API levels in parallel, builds an HTML board and a \"before | after\" PNG contact sheet, and a subagent writes the verdict. Also drives a device over adb: taps, text input, app launch, logs, screenshots. - \"check it on the emulator\", \"take before/after screenshots\", \"see how it looks on API 28/33/35\", \"run the flow in dark theme and gesture navigation\", \"check the bottom sheet / insets / navbar change\", \"launch the app on the emulator\", \"what is on the screen\", adb commands to a device."
argument-hint: "<what to check> [--api 28,33,35]"
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

The CLI is in `bin/` of this skill:

```bash
ADBM="${CLAUDE_SKILL_DIR}/bin/adbm"
```

If the variable is not substituted, take the folder from the "Base directory for this skill" line.

Run all commands from the project root: runs go to `<project>/build/adbm/<date>-<slug>/`.
Help for a command: `"$ADBM" <command> -h`.

## Just an action on the device

If you are asked to do something on a device without a layout check, run the command right away.
Examples: "install the APK", "open the screen", "tap", "type", "show the logs", "what is on the screen".
Then you do not need `doctor`, API selection, `new`, frames, `diff` or `board`.

```bash
"$ADBM" devices                              # devices and their API levels
"$ADBM" install app.apk --as after --api 35
"$ADBM" launch <package> --api 35
"$ADBM" ui --api 35                          # what is on the screen, as text
"$ADBM" tap --api 35 "Sign in"
"$ADBM" type --api 35 "user@example.com"
"$ADBM" key --api 35 back
```

Outside a run, `adbm` does not create `build/adbm/` in the project: its service files go to `~/.cache/adbm/`.
Logs, deep links, Wi-Fi, density, accessibility and other rare actions: raw adb from `reference/adb.md`.
Run `"$ADBM" doctor` only if something does not start.

All rules below apply to visual checks: frames, "before/after" comparison and flows.

## Token economy — rules first

A 1080×2400 image costs ~3350 tokens, a line of the UI tree ~15. So:

1. **Navigate by text only.** Read the screen with `adbm ui` or `adbm ui --find <text>`.
   Tap by selector: `adbm tap "Close"`. Do not guess coordinates from an image.
2. **`adbm diff` decides "did it change"**, not you. It reports the percent and area of change.
   For frames from `adbm shot` it also reports element shifts (`"Close" ↓48 px`): the UI tree is
   saved next to the frame. Maestro frames have no tree. Nobody looks at unchanged pairs.
3. **`adbm shot` and `adbm run` only save frames.** Do not open files from `api*/` with Read.
4. **If you cannot do without an image** — `adbm look` (540 px, ~860 tokens), `--small` (360 px, ~380),
   `--crop x0,y0,x1,y1` for a fragment. The output has `scale`: screen coordinate = image
   coordinate / scale. More than 3 `look` calls per task is a reason to stop and think.
5. **The `adbm-eyes` subagent judges the frames** (see "Check"). It looks at the contact sheet
   and the diff and returns up to 10 lines.
6. **Command output is short.** Details are in `<run>/logs/`. Read a log only on failure
   and only the part you need: `tail`, `grep`.

`<run>/stats.json` counts frames taken and images sent to the main context.

## Workflow

### 1. Environment

`"$ADBM" doctor`. If rows marked `missing` block the task, show them to the person with
the fix commands and ask whether to install. `adbm setup …` without `--yes` only prints the plan.
Details: `reference/setup.md`.

### 2. API levels

First find the app's `minSdk` and `targetSdk`: `grep -rn "minSdk\|targetSdk"` over `build.gradle*`
and `libs.versions.toml`. Do not offer emulators below `minSdk`. `adbm install` also reads
`minSdk` from the APK and skips such devices, and so does `adbm run`. If `targetSdk` ≥ 35,
edge-to-edge is enforced — a reason to include API 35.

By default check on one API level — 35. If the change touches system parts (insets, navbar,
theme, permissions, back navigation), offer a set of API levels with reasons from
`reference/api-matrix.md` and wait for the answer. Example: "Sheet insets → 28, 33, 35: edge-to-edge is enforced on 35".

`"$ADBM" devices --start 28,33,35` boots missing emulators. Always address a device by `--api N`:
the serial changes between launches.

### 3. Run folder and builds

```bash
"$ADBM" new <slug>                                   # new run folder
"$ADBM" install <before.apk> --as before --api 28,33,35
```

"Before": capture before the change, or build the base commit in a `git worktree` (`reference/setup.md`).
"After": the current code. A device holds one version at a time: first everything "before", then everything "after".

### 4. Actions: by hand or by flow

**By hand** — when you need one or two frames on one or two API levels and the path to the screen is short:

```bash
"$ADBM" prep --api 35 --theme dark            # animations off, status bar demo mode
"$ADBM" launch <package> --api 35 --clear
"$ADBM" ui --api 35                           # [3] Button "Close" id=close @540,1980 click
"$ADBM" tap --api 35 "Close"                  # text, content-desc, id; --scroll 4 to scroll
"$ADBM" shot 1-sheet --api 35 --as before     # frame into the run, not into the context
```

There are also `type` (ASCII), `key back|home|enter`, `swipe up|down`, `tap "[N]"` by number from `ui`.
Switches without a label show as `near="<row text>"`: tap the row text.
For a screen without a tree (Canvas, a game): `annotate` and `tap '#N'` through Android CLI.

**A flow is required** if any of these is true:
- the path to the screen is longer than 3–4 steps;
- you need a matrix of themes, navigation modes or font scales;
- three API levels or a "before/after" pair;
- the check will be repeated.

Then write a Maestro flow following `reference/flows.md` and run it:

```bash
"$ADBM" run .adbm/flows/<slug>.yaml --api 35                  # one API level first
"$ADBM" run .adbm/flows/<slug>.yaml --api 28,33,35 --as before \
  --matrix "nav=threebutton,gestural" "theme=light,dark"
```

Frame subfolders follow the axis order: `api35/before/gestural/dark/<frame>.png`.
Dark theme is not applied to the system UI on API 28, see `reference/api-matrix.md`.
`run` drives all API levels in parallel and prints one line per cell. On failure read
`logs/ui-fail-*.txt` (the screen tree) and the reason line, not a screenshot.

**Hangs and failures.** `adbm run` watches Maestro itself and prints its limits in the `watchdog:` line.
- **Silence** (`--stall`) — the longest wait in the flow (`timeout:` of `extendedWaitUntil` and others)
  plus 20 s, at least 45 s. Maestro prints a step only after it ends, so the limit
  must be longer than the longest step.
- **Cell** (`--timeout`) — 2 × the last successful run of this flow on this API level, at least 90 s.
  Without history — 600 s, a safety net: silence catches a hang earlier.
- **Set your own limit** only if you know more than `adbm`. Example: a step without an explicit `timeout`
  waits for the network or a long data load — better add `timeout:` to that step in the flow.

When a limit is exceeded, `adbm` kills Maestro and prints `HUNG … after step "…"`.
Next to it is a diagnosis: the device is offline, a system dialog "isn't responding" or "has stopped"
is on screen, or which window has focus. What to do:
- **device not responding** — `adbm devices`. If the emulator is missing,
  `adb -s <serial> emu kill`, then `adbm devices --start <API>`;
- **"isn't responding" or "has stopped" dialog** — this is a finding, not a tool failure:
  `logs/crash-*.txt`, `adb logcat -b crash`. Tell the person and close the dialog with `adbm tap`;
- **a foreign window has focus** (permission, keyboard, system dialog) — add a step to the flow;
- **the same step hangs twice** — do not retry a third time; show the person the step and the diagnosis.

Run your own long commands (`./gradlew`, `adbm run`) with a Bash timeout of at least 10 minutes
or in the background. Do not wait silently: no result in a reasonable time — check `adbm devices` and the log.

**Switching:** a manual check grew — `"$ADBM" save-flow <slug> --api 35`, then continue with the flow.

Record animations or "jumps" as video: `"$ADBM" record <name> --api 35 --seconds 5 --slow 3 -- <command>`.
You get an mp4 and a contact sheet `-sheet.png` for the subagent.

### 5. Check

```bash
"$ADBM" diff      # one line per changed pair, diff/*.png, diff/diff.json
"$ADBM" board     # index.html + manifest.js + 00-summary.png (if pairs ≤ 24, else one PNG per API)
```

Then start the `adbm-eyes` subagent. If ADBM is installed as a plugin, it is the `adbm:adbm-eyes` agent.
Otherwise use the Agent tool with `subagent_type: general-purpose`, `model: sonnet`, and as the prompt
the content of `agents/adbm-eyes.md` without frontmatter. In both cases add this block at the end of the prompt:

```
Task: <what was changed and what should come out>
Checklist: <2–6 items>
Run: <absolute path to the run folder>
Changed pairs:
<adbm diff output>
```

The subagent appends its verdict to `<run>/notes.md`. Then run `"$ADBM" board` again:
the board colours the frames. The statuses:
- **unchanged** — set by `adbm diff`; the subagent does not look at such pairs;
- **expected** — changed as intended;
- **problem** — a defect, or a change where none was expected;
- **review** — the subagent is not sure; a person should look.

If needed, open the board: `"$ADBM" board --open`.

### 6. Report to the person

- Path to the board: `<run>/index.html`.
- Summary in 3 lines: how many expected, problem, review, unchanged;
  what is broken and on which API levels.
- What to look at: 1–3 frames with paths.

## References

| File | When to read |
|---|---|
| `reference/setup.md` | SDK, system images, AVDs, Maestro, Android CLI, "before" build in a worktree |
| `reference/api-matrix.md` | which API levels and matrix axes to offer for a change |
| `reference/flows.md` | how to write and fix a Maestro flow |
| `reference/adb.md` | raw adb for rare actions: logs, deep links, Wi-Fi, accessibility |

## Limitations

- `adbm type` types ASCII only. Type non-Latin text in a flow with Maestro `inputText`.
- API 28 has no gesture navigation: `nav=gestural` cells are skipped.
- `prep --locale` works on API 33+ and needs `--app <package>`. `adbm run` finds the package itself:
  from `builds.json` or the flow's `appId`. A `locale` cell without a package or below API 33 is skipped.
- **Screenshot protection (`FLAG_SECURE`)** — common in banking apps and password managers. The frame
  comes out empty (Maestro: `Screenshot returned null`) or black. `run` and `shot` warn about it.
  Turn the protection off in the app as the first steps of the flow, or in a debug build.
- `adbm` sees physical devices, but when API levels match it picks the emulator.
  Address a physical device with `--serial`.
