# Visual check

Frames of the app on the HTML board (`<run>/index.html`) for the person, and a verdict if they want one.
Two kinds; take the first unless the task is about a change:

- **Screens** — the default. "Show me how it looks", "screenshots of these screens on API 33 and 35",
  "check the dark theme": the installed build (or one APK), frames, the board. No "before" build.
- **Before/after** — only to see what a change did: a fix, a refactoring, a bug that should be gone.
  Two builds, the same frames of each, the diff shows what changed.

Commands omit the prefix, as in `SKILL.md`: run `"$ADBM" <command>`.

## Steps

1. **Environment.** `doctor`; rows that block the task — show the fix and ask; `setup` without `--yes` only plans.
   `setup --hook` / `--agent` change the person's Claude Code settings: run them with `--yes` only after a clear yes.
2. **API levels.** The person named the levels — use them with `--api`, do not ask again and do not write
   the config; a change that needs another level (insets, theme, permissions) — mention it once.
   Otherwise `config` shows the project's set: `devices  apis=…`; commands without `--api` use it.
   `apis=-` (first check in the project): find `minSdk`/`targetSdk` in `build.gradle*`, offer a set with
   reasons from `reference/api-matrix.md` and wait for the answer. Then `config --set devices.apis=<list> --project`
   and `setup`: its plan downloads only the missing system images and AVDs. `devices --start <levels>` boots them.
3. **How to take frames.** By hand for 1–2 frames on 1–2 API levels: `prep`, `launch`, `tap`, `shot <name>`.
   A Maestro flow when the path is longer than 3–4 steps, for a theme/navigation/font matrix, for three
   API levels or when the check repeats: `flow new <slug>`, then try it with `run .adbm/flows/<slug>.yaml --api 35 --new`.
   `--new` gives the trial its own run, so its frames stay out of the check. Do it before step 4.
   Details, axes, video: `reference/workflow.md`; writing flows: `reference/flows.md`;
   a failed or hung `run`: `reference/troubleshooting.md`.
4. **Run and frames.** `new <slug>` — the run of the check.
   - Screens: `install <apk>` if the build is not on the devices yet, then the frames (`shot` or `run … --matrix …`).
   - Before/after: `install <before.apk> --as before`, "before" frames, then `install <after.apk>` and the same
     "after" frames. A "before" APK from the base commit: `reference/setup.md`, "Before" and "after" builds.
5. **Diff and board.** `diff`, then `board`. With one build `diff` says `after only` and marks frames that
   look the same on another API level (`≈ apiN`); the board shows the frames without "before"/"after".
   A verdict: start `adbm-eyes` (next section) — always for before/after; for screens when the person asked
   to check something (a checklist), not when they only want to see the screens.
6. **Report.** The board path (`board --open` shows it); with a verdict — counts of expected/problem/review/unchanged,
   what broke where, 1–3 frames.

**Which build a frame belongs to:** `--as before|after` on `shot`/`run`; without it — the build of the
last `install` (the run's `.as` file); with no install — `after`.

## The adbm-eyes subagent

Use the agent type `adbm-eyes` (`adbm:adbm-eyes` when ADBM is a plugin) if the Agent tool lists it.
Otherwise: Agent with `subagent_type: general-purpose` and as the prompt the content
of `agents/adbm-eyes.md` of this skill without frontmatter.

In both cases model and effort come from the person's settings: run `adbm config` and take
the `adbm-eyes` line. Pass its `model` and `effort` to the Agent tool, a value marked `(default)` too;
do not pass a value shown as `-`.
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

## Limits of the check

- **`FLAG_SECURE`** (banks, password managers): empty or black frames — see `reference/troubleshooting.md`.
- API 28: no gesture navigation (`nav=gestural` cells are skipped); dark theme does not reach its system UI.
