# Visual check

For "how does it look", "what changed", before/after builds, several API levels, a theme or navigation
matrix. Commands omit the prefix, as in `SKILL.md`: run `"$ADBM" <command>`.

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
4. **Run and builds.** `new <slug>` — the run of the check. Comparing builds: `install <before.apk> --as before`,
   "before" frames (`run … --matrix …` or `shot`), then `install <after.apk>` and the same "after" frames.
   A "before" APK from the base commit: `reference/setup.md`, "Before" and "after" builds.
   One build as installed: frames only, `diff` says `after only`.
5. **Diff and board.** `diff`, then `board`. Then start `adbm-eyes` (next section).
6. **Report.** `<run>/index.html`; counts of expected/problem/review/unchanged; what broke where; 1–3 frames.

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
