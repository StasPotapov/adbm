# Maestro flows for adbm

Maestro is an open-source UI testing tool. A flow is a YAML file with steps.
Maestro finds elements by the accessibility tree and waits for them by itself.
No LLM takes part in a run, so the run is the same on every API level.

Command reference: https://docs.maestro.dev/api-reference/commands

## Where flows live

`<project>/.adbm/flows/<slug>.yaml` — in the project's git. Runs (`build/adbm/`) do not go to git.

## Steps

1. Explore the screen: `adbm ui --api 35`, `adbm ui --find "<text>"`.
2. Write the flow by the rules below.
3. Run it on one API level: `adbm run .adbm/flows/<slug>.yaml --api 35`.
4. On failure read the reason line and `logs/ui-fail-*.txt`, fix the flow, repeat.
5. Run it on all chosen API levels: `adbm run … --api 28,33,35 --matrix "nav=…" "theme=…"`.

## Rules

- **Selectors** come from `adbm ui`: `text`, `id`, `accessibilityText`.
  Text in `tapOn` is a regular expression: `"(Display|Экран).*"` covers two locales.
  Escape dots, brackets and `+` in the text: `"Price \\(USD\\.\\)"`.
- **Coordinates** — only in percent and with a comment why there is no selector:
  ```yaml
  # the button has no text and no id, it is drawn on a Canvas
  - tapOn:
      point: "50%,90%"
  ```
- **Waits** — `extendedWaitUntil` or `assertVisible`, no `sleep`.
  Put `waitForAnimationToEnd` before every `takeScreenshot`.
  Give a long step an explicit `timeout:`: the `adbm run` watchdog sets its silence limit from it.
- **State** — a flow starts with `launchApp: {clearState: true}`. The exception is system apps
  such as Settings: do not clear their data, use `stopApp` + `launchApp`.
  Do not set theme, navigation, font scale or demo mode in the flow: `adbm prep` sets them from `--matrix`.
- **Frame names** — `takeScreenshot: "<N>-<state>"`, for example `"3-sheet-expanded"`.
  Do not put the API level, "before/after" or the matrix cell into the name: `adbm` sorts frames into folders.
- **One flow — one check.** Themes and navigation come from `--matrix`, not from copies of the file.
- **Scroll to an element** — `scrollUntilVisible`, then `tapOn`.
- **Non-Latin text in a field** — `inputText: "Привет"` works: checked with Maestro 2.11.0 on API 28, 33
  and 35 (the Maestro docs still say Android takes ASCII only). By hand outside a flow — `adbm type`: it pastes such text through the clipboard with mobilecli, else uses Maestro.

## Template

```yaml
appId: com.example.app
---
- launchApp:
    clearState: true
- extendedWaitUntil:
    visible: "Catalog"
    timeout: 10000
- tapOn: "Catalog"
- scrollUntilVisible:
    element:
      id: "item_42"
    direction: DOWN
- tapOn:
    id: "item_42"
- waitForAnimationToEnd
- takeScreenshot: "1-item-details"
- tapOn: "Open sheet"
- waitForAnimationToEnd
- takeScreenshot: "2-sheet-peek"
```

Variables: `adbm run flow.yaml -e USER=test` → `${USER}` in the flow.

## From a manual session

Every successful `adbm launch`, `tap`, `type`, `clear-field`, `key`, `swipe`, `open`, `stop`, `clear`,
`shot`, `wait`, `assert` is logged to `~/.cache/adbm/session.jsonl`
together with the project path. `adbm save-flow <slug> --api 35` builds a flow from the last `launch`
of the current project:
- `launch --clear` becomes `clearState: true`, without `--clear` — `false`;
- selector text is escaped as a regular expression;
- `tap --scroll N` becomes `scrollUntilVisible` + `tapOn`;
- a tap by coordinates becomes a `point` in percent marked `TODO`;
- `wait` and `tap --expect` become `extendedWaitUntil` (`visible`, or `notVisible` for `wait --gone`)
  with the same timeout, at least 5 s; `assert` becomes `assertVisible`. A match by id gives `id:`,
  a substring match gives `.*text.*`;
- `tap --long` / `--double` become `longPressOn` / `doubleTapOn`; `swipe x0,y0,x1,y1` becomes
  `swipe` with `start`/`end` in percent; `open` becomes `openLink`; `clear-field` becomes `eraseText`;
  `stop` becomes `stopApp`, `clear` becomes `clearState`; `uninstall` becomes a `TODO` comment.

After `save-flow` run the flow once and fix the selectors.

## Failure

A failed or hung cell, black frames, device problems: `troubleshooting.md`.

## Screenshot protection

If the app window has `FLAG_SECURE`, Maestro fails on some API levels with `Screenshot returned null`
and silently returns a black frame on others. `adbm run` drops empty frames, keeps black ones
and marks the cell as failed, with a hint. A frame counts as black when its middle part
(without the system bars) is uniformly black: a dark theme with any visible text passes. The fix is to turn the protection off as the first steps of the flow:

```yaml
# the app sets FLAG_SECURE by default
- tapOn: "Settings"
- tapOn: "Security"
- tapOn: "Screenshot protection"
- back
- back
```

Compose switches have no text in the tree. `adbm ui` shows them with the row label:
`[22] near="Block screenshots…" click,check`. Tap the row text.

## Parallel runs

`adbm run --api 28,33,35` starts a separate `maestro --device <serial> test` process
per device. Tested on 15.10.2026: three emulators take ~18 s, one after another it would be ~49 s (13 + 20 + 16),
and frames do not get mixed up. `maestro --shard-all` is not used: it failed on one device
and names folders `flow-shard-N` without a link to the device.
