# Visual check in detail

`reference/visual-check.md` gives the order of steps. Here is how each step works.

## API levels

The project's set is `[devices] apis` (`adbm config`); commands without `--api` use it. When it is empty,
ask the person and write the answer with `adbm config --set devices.apis=… --project` (`reference/visual-check.md`, step 2).

Find `minSdk` and `targetSdk`: `grep -rn "minSdk\|targetSdk"` over `build.gradle*` and
`libs.versions.toml`. Do not offer emulators below `minSdk`. `adbm install` also reads `minSdk` from
the APK and skips such devices, and so does `adbm run`. If `targetSdk` ≥ 35, edge-to-edge is enforced —
a reason to include API 35. Example of an offer: "Sheet insets → 28, 33, 35: edge-to-edge is enforced on 35".

`adbm devices --start` (or `--start 28,33,35`) boots missing emulators and waits until the package manager answers.

## Builds

"Before": capture it before the change, or build the base commit in a `git worktree` (`setup.md`).
"After": the current code. `adbm install` writes `builds.json` (package, sha1, minSdk) and the run's `.as`
file only after a successful install on at least one device. It warns when "before" and "after" are
different packages. Without `--as` the build is `after`.

## Frames by hand

When you need one or two frames on one or two API levels and the path to the screen is short:

```bash
"$ADBM" new <slug>                            # frames go to this run; without it — to the cache, unseen by diff
"$ADBM" prep --api 35 --theme dark            # animations off, status bar demo mode, checked
"$ADBM" launch <package> --api 35 --clear
"$ADBM" ui --api 35                           # [3] Button "Close" id=close click; --xy adds @x,y
"$ADBM" tap --api 35 "Close" --expect "Saved" # text, content-desc, id; --scroll 4 to scroll
"$ADBM" shot 1-sheet --api 35 --as before     # the frame goes to the run, not to the context
```

`prep --theme` sets the system theme. An app may have its own theme setting on top of it: check
which one the task is about. An in-app theme is not a `--matrix` axis: every app sets it its own way.
Put the steps that set it into the flow under a condition on a variable, and run once per value:
`run <flow> -e APP_THEME=dark --group app-dark`, then `-e APP_THEME=light --group app-light`. In the flow:

```yaml
- runFlow:
    when:
      true: ${APP_THEME == "dark"}
    commands:
      - tapOn: "Dark theme"
```

Other input: `type`, `clear-field`, `key back|home|enter|hide-keyboard`, `swipe up|down|x0,y0,x1,y1`,
`tap --long|--double`, `tap "[N]"`, `rotate`. Switches without a label show as `near="<row text>"`:
tap the row text. A screen without a tree (Canvas, a game): `annotate` and `tap '#N'` through Android CLI. If it is not installed,
offer `adbm setup --android-cli --yes` with the reason and run it only after a clear yes; until then tap by `x,y` from `look`.
`shot` saves the UI tree next to the frame, so `adbm diff` reports element shifts (`"Close" ↓48 px`).

A manual check grew — `adbm save-flow <slug> --api 35` turns the journal of `launch`, `tap`, `type`,
`key`, `swipe`, `wait`, `assert`, `shot` into a flow; then continue with the flow.

## Flows and the matrix

```bash
"$ADBM" flow new <slug>                                      # template in .adbm/flows/
"$ADBM" run .adbm/flows/<slug>.yaml --api 35                 # one API level first
"$ADBM" run .adbm/flows/<slug>.yaml --api 28,33,35 --as before \
  --matrix "nav=threebutton,gestural" "theme=light,dark"
```

- Frame subfolders follow the axis order: `api35/before/gestural/dark/<frame>.png`.
- Axes: `theme`, `nav`, `font` (font scale), `locale` (API 33+). `run` finds the app package itself (from
  `builds.json` or the flow's `appId`); a `locale` cell without a package or below API 33 is skipped.
  By hand, `prep --locale` needs `--app <package>`.
- Axes outside `--matrix` take what `adbm prep` set by hand on that device, else the defaults: light theme,
  three-button navigation, font scale 1.0. `prep --reset` restores the defaults and forgets the hand-set values.
- `prep` checks that the device took each setting; a cell whose setting did not apply fails.
- `run` checks that the app is installed, drives all API levels in parallel and prints one line per cell.
- Keep flows in `<project>/.adbm/flows/`: `run` warns about a flow elsewhere.
- Run long commands (`./gradlew`, `adbm run`) with a Bash timeout of at least 10 minutes or in the background.

## Video

Animations and "jumps": `adbm record <name> --api 35 --seconds 5 --slow 3 -- <command>`.
You get an mp4 and a contact sheet `-sheet.png` for the subagent.

## The check

```bash
"$ADBM" diff      # one line per changed pair; diff/*.png 540 px, *.crop.png, *.top.png, diff.json
"$ADBM" board     # index.html + 00-summary.png of changed pairs (≤ 24 frames, else one PNG per API)
```

`adbm diff` compares the status bar apart from the content and marks a pair `≈ apiN` when it changed
the same way as on another API level. Frames only "after" (one build): it prints `after only: N frames of one build, nothing to compare with`,
and the subagent judges every frame by the checklist. A frame without its pair is listed as
`no before frame` or `no after frame`.

Statuses on the board:
- **unchanged** — set by `adbm diff`; the subagent does not look at such pairs;
- **expected** — changed as intended;
- **problem** — a defect, or a change where none was expected;
- **review** — the subagent is not sure; a person should look.

`board` warns when changed frames have no verdict or `notes.md` has no `adbm-eyes` section.
