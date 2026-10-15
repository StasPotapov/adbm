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

The CLI is `bin/adbm` of this skill: `ADBM="${CLAUDE_SKILL_DIR}/bin/adbm"`. If the variable is not
substituted, take the folder from the "Base directory for this skill" line. Run commands from the
project root: runs go to `<project>/build/adbm/<date>-<slug>/`. The project is the git root of the
current folder; `ADBM_PROJECT=<path>` overrides it. Help: `"$ADBM" <command> -h`. Commands below
omit the prefix: run `"$ADBM" <command>`, and set the variable in every Bash call (it does not persist).

## Request → first command

| The person asks | Run |
|---|---|
| what is on the screen | `ui --api 35` (`--find <text>` to narrow) |
| tap, open a screen | `tap "<text>" --expect "<text on the next screen>"` |
| type into a field | `type "<text>"`; non-Latin — see "Limitations" |
| install, launch, stop, clear data | `install <apk>`, `launch <pkg>`, `stop`, `clear`, `uninstall` |
| logs, crash | `log` (the app's process), `log --crash`, `log --grep <re>` |
| deep link, permission, file | `open <uri>`, `perm <pkg> grant CAMERA`, `push`, `pull` |
| which devices, boot an emulator | `devices`, `devices --start 33,35`, `devices --stop 33` |
| device theme, navigation mode, font scale | `prep --theme dark`, `--nav gestural`, `--font-scale 1.3` |
| how it looks, before/after, several API levels, themes | "Visual check" below |

A single action needs no `doctor`, `new`, `diff` or `board`. Only `new` and `run` start a run; outside one
`adbm` writes to `~/.cache/adbm/`, and `shot`/`record` frames there are unseen by `diff` and `board`.
Rare actions: `reference/adb.md`. `doctor` only if something does not start. Address devices by `--api N`.

## Token economy

A 1080×2400 image costs ~3350 tokens, a line of `adbm ui` ~15.

1. **Navigate by text.** `ui`, then `tap "<text>"`. `tap` prints what appeared, went away and switches that flipped;
   `--expect` confirms the next screen in one line. Do not call `ui` after every tap.
   A tap by `x,y` or `#N` prints no change — add `--expect`. `[N]` from `ui` works only on that screen.
2. **Do not open frames.** `shot` and `run` save frames to the run, not to the context. Never `Read` a file
   from `api*/`. `adbm diff` decides what changed; the `adbm-eyes` subagent looks at images.
3. **One picture when nothing else helps:** `look` (540 px, ~860 tokens), `--small` (~380), `--crop` (up to
   ~1850). Screen coordinate = image coordinate / `scale` from the output. Over 3 `look` per task — stop.
4. **Logs:** read only on failure and only the part you need (`tail`, `grep`).

`adbm status` estimates what `adbm` put into the context. If the guard hook is installed (plugin, or
`settings.json` per the README), it denies `Read` of a frame or a raw XML dump: do what the denial says.

## Visual check

1. **Environment.** `doctor`; `missing` rows that block the task — show the fix and ask; `setup` without `--yes` only plans.
2. **API levels.** Find `minSdk`/`targetSdk` in `build.gradle*`. Default — API 35 only. For insets, navbar,
   theme, permissions, back navigation offer a set with reasons from `reference/api-matrix.md` and wait.
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
Otherwise: Agent with `subagent_type: general-purpose`, `model: sonnet`, and as the prompt the content
of `agents/adbm-eyes.md` of this skill without frontmatter. Append to the prompt:

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
| `reference/setup.md` | SDK, AVDs, Maestro, Android CLI, a "before" build in a worktree |
| `reference/adb.md` | raw adb for what `adbm` does not do |

## Limitations

- **Non-Latin text:** `input text` cannot type it, so `adbm type` sends it through Maestro `inputText`
  (~10 s instead of ~1 s). In a flow write `inputText` as usual.
- **`FLAG_SECURE`** (banks, password managers): empty or black frames — see `reference/troubleshooting.md`.
- API 28: no gesture navigation (`nav=gestural` cells are skipped); dark theme does not reach its system UI.
- A physical device is picked only when no emulator has that API level: address it with `--serial`.
