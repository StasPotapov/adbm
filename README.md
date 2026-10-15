# ADBM — Android Debug Bridge Matrix

[Русский](README.ru.md)

A Claude Code skill and the `adbm` CLI for visual checks of Android apps by an agent.
The agent boots emulators for the API levels you need, installs "before" and "after" builds
and runs one scenario on all API levels in parallel. The result is an HTML board and a
"before | after" PNG contact sheet with a verdict.

The main goal is a small token budget. A 1080×2400 screenshot costs a model ~3350 tokens,
so screenshots never enter the agent's context:

- **the agent navigates by text** — `adbm ui` shrinks the UI tree 10–20×, `adbm tap "Close"`;
- **"did it change" is computed in Python** — `adbm diff` reports percent and area, and element shifts for frames from `adbm shot`;
- **a subagent looks at the images** on a cheaper model and returns up to 10 lines;
- **when a picture is unavoidable** — `adbm look` returns a 540 px frame (~860 tokens) or a crop.

## Commands

| Command | What it does |
|---|---|
| `adbm doctor` | checks SDK, adb, emulator, Java, Maestro, Pillow, AVDs and their `config.ini` |
| `adbm setup --api 28,33,35` | system images, AVDs with 4 GB RAM, Maestro, Android CLI; without `--yes` it only prints the plan |
| `adbm devices --start 28,33,35` | boots emulators, prints API → serial → screen |
| `adbm prep` | animations off, status bar demo mode, theme, navigation mode, font scale |
| `adbm new <slug>`, `adbm status` | start a run folder, show the current run and counters |
| `adbm install <apk> --as before\|after` | installs an APK on all API levels in parallel |
| `adbm ui`, `tap`, `launch`, `type`, `key`, `swipe` | navigation by UI tree text |
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

Requires the Android SDK and Python 3.9+ with Pillow. Scenarios need Maestro, video needs ffmpeg.

```bash
git clone <repo> ~/dev/adbm
ln -s ~/dev/adbm/skill ~/.claude/skills/adbm
python3 -m pip install Pillow
~/dev/adbm/skill/bin/adbm doctor
```

The CLI works without Claude Code too: `ln -s ~/dev/adbm/skill/bin/adbm /usr/local/bin/adbm`.

**Guard hook.** `skill/hooks/adbm-guard.py` denies `Read` of a full-size frame or a raw UI dump,
so an agent cannot spend ~3350 tokens on one screenshot by accident. As a plugin, ADBM registers it
itself (`skill/hooks/hooks.json`). With the symlink install, add it to `~/.claude/settings.json`:

```json
"hooks": {
  "PreToolUse": [{ "matcher": "Read", "hooks": [{ "type": "command",
    "command": "f=~/.claude/skills/adbm/hooks/adbm-guard.py; [ -f \"$f\" ] || exit 0; exec python3 \"$f\"" }] }]
}
```

**Measuring a session.** `tools/measure-session.py <transcript.jsonl>` prints what a Claude Code
session spent on `adbm`: characters of output per command and images read.
`adbm status` prints the same estimate for the current run from `stats.json`.

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
