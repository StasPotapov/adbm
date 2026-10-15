# When something fails

## A cell of `adbm run` failed

The line has the reason from Maestro and the path to the log. Next to it:
- `logs/ui-fail-<cell>.txt` — the screen tree at the moment of failure (up to 80 lines);
- `logs/crash-<cell>.txt` — the last 60 lines of the crash buffer, if the app crashed.

Fix the flow from these files. Do not open the failure screenshot if the tree answers the question.
`not installed on API N` — run `adbm install` for that API level. `prep: error — …` — the device did not
take a theme, navigation or font setting: `adbm prep` by hand on that API level shows the same error.

## `adbm run` hangs

`adbm run` watches Maestro itself and prints its limits in the `watchdog:` line.
- **Silence** (`--stall`) — the longest wait in the flow and the flows it includes via `runFlow`
  (`timeout:` of `extendedWaitUntil` and others) plus 20 s, at least 45 s. Maestro prints a step
  only after it ends, so the limit must be longer than the longest step. Before Maestro's first
  output line the limit is at least 120 s: JVM start and driver install print nothing.
- **Cell** (`--timeout`) — 2 × the slowest last successful run of this flow among the chosen API levels,
  at least 90 s. Without history — 600 s, a safety net: silence catches a hang earlier.
- **Set your own limit** only if you know more than `adbm`. Example: a step without an explicit `timeout`
  waits for the network or a long data load — better add `timeout:` to that step in the flow.

When a limit is exceeded, `adbm` kills Maestro and prints `HUNG … after step "…"` with a diagnosis:
- **device not responding** — `adbm devices`. If the emulator is missing or offline:
  `adbm devices --stop <API>`, then `adbm devices --start <API>`;
- **"isn't responding" or "has stopped" dialog** — a finding, not a tool failure: `logs/crash-*.txt`,
  `adbm log --crash`. Tell the person and close the dialog with `adbm tap`;
- **a foreign window has focus** (permission, keyboard, system dialog) — add a step to the flow,
  or grant the permission before the run: `adbm perm <pkg> grant <PERMISSION>`;
- **the same step hangs twice** — do not retry a third time; show the person the step and the diagnosis.

Do not wait silently: no result in a reasonable time — check `adbm devices` and the log.

## Black or empty frames: screenshot protection

If the app window has `FLAG_SECURE`, Maestro fails on some API levels with `Screenshot returned null`
and returns a black frame on others. `run` drops empty frames, keeps black ones as evidence and marks
the cell failed; `shot` warns. A frame counts as black when its middle part (without the system bars)
is uniformly black: a dark theme with any visible text passes. Turn the protection off in the app as
the first steps of the flow (`flows.md`, "Screenshot protection"), or use a debug build without it.

## Devices

| Symptom | What to do |
|---|---|
| `adbm devices` lists a device as `offline` | `adb kill-server`, then `adbm devices`; an emulator — `devices --stop N`, `--start N` |
| `unauthorized` | accept the USB debugging prompt on the device |
| `no device with API N` | `adbm devices --start N`; no AVD — `adbm setup --api N --yes` |
| `uiautomator dump failed` | an animation or a busy app: `adbm prep`, retry; `wait` and `tap --expect` retry by themselves |
| `[N] … is no longer on the screen` | the screen changed since `adbm ui`: run `ui` again, or tap by text |
| a command hangs | `timeout 10 adb …` for raw adb; `adbm devices` to see the state |
