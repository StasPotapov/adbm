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
- **a subagent looks at the images** on a cheaper model and returns up to 10 lines;
- **when a picture is unavoidable** — `adbm look` returns a 540 px frame (~860 tokens) or a crop.

## Commands

| Command | What it does |
|---|---|
| `adbm doctor` | checks SDK, adb, emulator, Java, Maestro, Pillow, AVDs and their `config.ini`, the guard hook, the `adbm-eyes` agent and the subagent models |
| `adbm config` | model and effort of subagents from `~/.config/adbm/config.ini` and `.adbm/config.ini`; `--init` writes a file with the defaults |
| `adbm setup --api 28,33,35` | system images, AVDs with 4 GB RAM, Maestro, Android CLI; `--hook`, `--agent` for Claude Code; without `--yes` it only prints the plan |
| `adbm devices --start 28,33,35` | boots emulators, prints API → serial → screen |
| `adbm prep` | animations off, status bar demo mode, theme, navigation mode, font scale |
| `adbm new <slug>`, `adbm status` | start a run folder, show the current run and counters |
| `adbm install <apk> [--as before\|after]` | installs an APK on all API levels in parallel (`after` by default) |
| `adbm launch`, `stop`, `clear`, `uninstall`, `open <uri>`, `perm`, `log` | app control: launch, force-stop, data, deep link, permissions, logcat tail |
| `adbm push`, `pull`, `rotate`, `devices --stop`, `clean` | files, orientation, stop emulators, delete old runs (keeps 5; without `--yes` only prints the plan) |
| `adbm flow new <slug>` | a flow template in `.adbm/flows/` |
| `adbm ui`, `tap`, `wait`, `assert`, `type`, `clear-field`, `key`, `swipe` | navigation by UI tree text; `tap` prints what changed on the screen, `--expect` waits for the next screen |
| `adbm shot`, `look`, `thumb`, `annotate`, `record` | frames into the run folder, a downscaled frame or crop, video |
| `adbm run <flow.yaml> --matrix …` | a Maestro flow on all API levels in parallel, theme and navigation matrix |
| `adbm save-flow` | manual session → Maestro flow |
| `adbm diff` | pixel diff (540 px, crops, status bar apart), UI tree diff, `≈ apiN` for the same change on another API |
| `adbm board` | HTML board and `00-summary.png` contact sheet |

Subfolders follow the order of axes in `--matrix`. A run is stored in `<project>/build/adbm/<date-time>-<slug>/`:

```
api35/before/gestural/dark/1-peek.png
api35/after/gestural/dark/1-peek.png
diff/api35/gestural/dark/1-peek.png
logs/  notes.md  stats.json  builds.json
index.html  manifest.js  00-summary.png
```

## Install

Requires the Android SDK and Python 3.9+ with Pillow. Scenarios and non-ASCII `adbm type` need Maestro, video needs ffmpeg.

```bash
git clone <repo> ~/dev/adbm
ln -s ~/dev/adbm/skill ~/.claude/skills/adbm
python3 -m pip install Pillow
~/dev/adbm/skill/bin/adbm setup --hook --agent --yes   # guard hook + adbm-eyes agent
~/dev/adbm/skill/bin/adbm doctor
```

The CLI works without Claude Code too: `ln -s ~/dev/adbm/skill/bin/adbm /usr/local/bin/adbm`.

**Guard hook.** `skill/hooks/adbm-guard.py` denies `Read` of a full-size frame or a raw UI dump,
so an agent cannot spend ~3350 tokens on one screenshot by accident. As a plugin, ADBM registers it
itself (`skill/hooks/hooks.json`). With the symlink install `adbm setup --hook --yes` appends it to
`hooks.PreToolUse` in `~/.claude/settings.json` (`$CLAUDE_CONFIG_DIR` if set). It keeps the other settings and the
file mode; a copy of the old file goes to `settings.json.adbm-backup` next to the real file (through a symlink —
next to its target). It changes Claude Code for every project, so it runs only with `--yes` after the person agrees.
`adbm doctor` reports the hook as `missing` until then. By hand, the block is:

```json
"hooks": {
  "PreToolUse": [{ "matcher": "Read", "hooks": [{ "type": "command",
    "command": "f=~/.claude/skills/adbm/hooks/adbm-guard.py; [ -f \"$f\" ] || exit 0; exec python3 \"$f\"" }] }]
}
```

**Subagent models.** The `adbm-eyes` subagent runs on `sonnet` by default, with no effort set:
the agent keeps its usual effort. To change the model or effort, create a settings file and edit it:

```bash
adbm config --init            # ~/.config/adbm/config.ini ($XDG_CONFIG_HOME if set), for all projects
adbm config --init --project  # .adbm/config.ini, for this project only
adbm config                   # the effective values and where they come from
```

```ini
[adbm-eyes]
model = haiku     # sonnet, opus, haiku, fable; empty — the default of the agent type
effort = low      # low, medium, high, xhigh, max; empty — the usual effort
```

The project file overrides the user file. If the `adbm-eyes` type is not installed,
the skill starts `general-purpose`, and an empty `model` there means the main session's model. Before it starts the subagent, the skill runs `adbm config`
and passes `model` and `effort` to the Agent tool. This works only in Claude Code.
If you use another tool (Codex and others), adapt the "The adbm-eyes subagent" section
of `skill/SKILL.md` and `skill/agents/adbm-eyes.md` to it.

**Measuring a session.** `tools/measure-session.py <transcript.jsonl>` prints what a Claude Code
session spent on `adbm`: characters of output per command and images read.
`adbm status` prints the same estimate for the current run from `stats.json`.

## Tests

```bash
python3 -m unittest discover tests
```

No device is needed: the tests cover the UI tree parser, the matrix, the diff, verdicts, `save-flow`,
the guard hook and the session measurement on fixtures from a real run. Without Pillow the image tests are skipped.

## Example

```bash
adbm new sheet-insets
adbm install before.apk --as before --api 28,33,35
adbm run .adbm/flows/sheet.yaml --api 28,33,35 --matrix "nav=threebutton,gestural" "theme=light,dark"
adbm install after.apk --as after --api 28,33,35
adbm run .adbm/flows/sheet.yaml --api 28,33,35 --as after --matrix "nav=threebutton,gestural" "theme=light,dark"
adbm diff
adbm board --open
```

## Why not …

- **Google's Android CLI** — journeys are executed by an LLM, so runs are not deterministic. The binary
  is closed source and telemetry is on by default. ADBM uses it only for `annotate`.
- **mobile-mcp and similar MCP servers** — interactive, keep screenshots in context, one device at a time.
- **Roborazzi, Paparazzi, Shot** — need test code and golden images in git. ADBM compares two builds.
- **Percy, Emerge, Applitools** — cloud and paid.

## License

MIT
