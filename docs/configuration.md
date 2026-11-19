# Configuration

[Русский](configuration.ru.md) · [README](../README.md)

## Settings files

Settings live in two INI files:

- `~/.config/adbm/config.ini` applies to all projects (`$XDG_CONFIG_HOME/adbm/` if the variable is set);
- `.adbm/config.ini` in the project root applies to this project only and overrides the user file.

```bash
adbm config                                    # the effective values and where they come from
adbm config --set devices.apis=28,33,35 --project   # one value into the project file
adbm config --set adbm-eyes.model=sonnet       # one value into the user file
adbm config --init                             # the user file with all keys and comments
adbm config --init --project                   # the project file: keys are commented out and override nothing
```

`--set` keeps comments and the other keys. `adbm config` and `adbm doctor` show an error in a file
as a line with `!`. A bad value is not applied, and the default stays in effect.

## API levels

```ini
[devices]
apis = 28, 33, 35               # empty — the one running emulator, or API 35
image = google_apis             # image variant for new AVDs; not set — any phone image already on disk
profile = pixel_8               # profile of new AVDs, see avdmanager list device
```

Multi-device commands use `apis` if you pass neither `--api` nor `--serial`. Start the configured
emulators with `adbm devices --start`. A single-device command picks one running device or asks you
to choose. A list for all projects can go to `~/.config/adbm/config.ini`; an empty project value does not override it.

On the first check in a project `apis` is empty. The agent reads the app's `minSdk`, offers levels
with reasons and waits for the answer. Then it writes the answer: `adbm config --set devices.apis=28,33,35 --project`.
Which levels fit which change is in [skill/reference/api-matrix.md](../skill/reference/api-matrix.md).

No link to images is needed. `adbm setup` builds a plan: [`sdkmanager`](https://developer.android.com/tools/sdkmanager) downloads the missing images from
Google's repository into `$ANDROID_HOME/system-images/`, and [`avdmanager`](https://developer.android.com/tools/avdmanager) creates [AVDs](https://developer.android.com/studio/run/emulator). `setup` skips a level
that already has a phone AVD (Wear, TV, Automotive and tablet AVDs do not count) and reuses an image already on disk. If `image` or `profile` differs from an existing AVD,
`setup` says so and leaves the AVD alone: delete it to recreate it.

To add a level, append the number to `apis` and run `adbm setup`. Without `--yes` it only prints the plan.

## Subagent model

```ini
[adbm-eyes]
model = haiku     # sonnet, opus, haiku, fable; empty — the default of the agent type
effort = low      # low, medium, high, xhigh, max; empty — the usual effort
```

By default the `adbm-eyes` [subagent](https://code.claude.com/docs/en/sub-agents) runs on `haiku` with effort `low`.

A strong model is not needed here: deterministic checks do the main work. `adbm diff` finds the changed
pairs, the area and the changed percent without a model, and compares the status bar apart. The model only
explains the result: it writes what exactly broke and marks the pairs with a problem. If the model is wrong,
the changed pair still stays on the board, and a person sees it.

On the [example run](example.md), `haiku` and `sonnet` gave the same verdict: 6 PROBLEM and 2 EXPECTED.
At `high` effort, the subagent spent more tokens and missed the light navigation bar.

These model and effort settings apply to Claude Code. The skill passes them when the Agent tool
supports those parameters. Codex and other clients use their own subagent APIs and models.
See [the launch instructions](../skill/reference/visual-check.md#the-adbm-eyes-subagent).

## Guard hook

The [Claude Code hook](https://code.claude.com/docs/en/hooks) `skill/hooks/adbm-guard.py` denies `Read` of a full-size frame or a raw UI dump, so an agent cannot
spend ~3350 tokens on one screenshot by accident.

- **A plugin install** registers the hook itself (`skill/hooks/hooks.json`).
- **A symlink install:** `adbm setup --hook --yes` appends the hook to `hooks.PreToolUse` in
  `~/.claude/settings.json` (`$CLAUDE_CONFIG_DIR` if set). It keeps the other settings and the file mode.
  A copy of the old file goes to `settings.json.adbm-backup` next to the real file (through a symlink —
  next to its target).

The hook changes Claude Code for every project, so it runs only with `--yes` after the person agrees.
`adbm doctor` reports the hook as a warning (`!`) until then. By hand, the block is:

```json
"hooks": {
  "PreToolUse": [{ "matcher": "Read", "hooks": [{ "type": "command",
    "command": "f=~/.claude/skills/adbm/hooks/adbm-guard.py; [ -f \"$f\" ] || exit 0; exec python3 \"$f\"" }] }]
}
```

## The adbm-eyes agent

`adbm setup --agent --yes` links `~/.claude/agents/adbm-eyes.md` to `skill/agents/adbm-eyes.md`.
A regular file in its place is copied to `adbm-eyes.md.adbm-backup`. A plugin install has the agent already.
Without the installed agent, Claude Code can use `general-purpose` with the same prompt. Codex and
other clients use the [shared prompt](../skill/agents/adbm-eyes.md) without this install.
