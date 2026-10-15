# Example run

[Русский](example.ru.md) · [README](../README.md)

This is a real run on the MyPassBox app. The change switched the default theme from "System"
to "Dark". The agent checked three screens on API 33 and 35 with a light and a dark system theme.

## Commands

```bash
adbm new mypassbox-dark-default
adbm install before.apk --as before --api 33,35
adbm run .adbm/flows/theme-default.yaml --api 33,35 --as before --matrix theme=light,dark
adbm install after.apk --as after --api 33,35
adbm run .adbm/flows/theme-default.yaml --api 33,35 --as after --matrix theme=light,dark
adbm diff
adbm board --open
```

If the project settings list the API levels, `--api` can be left out
(see [configuration.md](configuration.md)).

## 1. Builds and scenario

`adbm install` installs the "before" build on all emulators at once, later the "after" build. `adbm run` runs
one [Maestro flow](https://docs.maestro.dev) on all API levels in parallel, in every cell of the `theme=light,dark` matrix.
Frames go to the run folder, not into the agent's context.

## 2. Diff

`adbm diff` compares "before | after" pairs pixel by pixel and prints one line per pair:

```
api33/dark/2-settings: 2.5% @45,483-1035,582
api35/dark/2-settings: ≈ api33: the same change
api33/light/1-empty-list: 94.4% @0,96-1080,2274 · status bar differs
api35/light/1-empty-list: ≈ api33: the same change
…
pairs 12, changed 8 (4 same as another API), unchanged 4 · diff images: diff/
```

Nobody looks at unchanged pairs after this. The `≈` mark means the pair changed the same way on another API level.
For a small change the diff cuts a crop: "before" on top, "after" below. Here it is the theme switch:

![Diff crop: the theme switch before and after](img/diff-crop.png)

The diff compares the status bar apart. This crop shows the defect: in "after" the clock and icons are dark on a dark background.

![Status bar crop before and after](img/diff-statusbar.png)

## 3. Verdict

The `adbm-eyes` subagent looks at the contact sheet and crops against the task checklist.
For every changed pair it writes a verdict: EXPECTED — as intended, PROBLEM — a defect, REVIEW — a person should look.
The main agent gets up to 10 lines of text and opens no images.

The `00-summary.png` contact sheet puts all changed pairs on one image. The subagent looks at it,
and a person uses it for a quick look:

![Before and after contact sheet](img/summary.png)

## 4. Board

`adbm board` builds an HTML page: the summary, verdicts, frame pairs with the changed percent,
an API filter and a "changed only" mode.

![Run board: summary, verdicts and a PROBLEM pair](img/board.png)

## Result

The dark default theme works. But with a light system theme the status bar clock and icons
became dark on a dark background, and the navigation bar stayed light. The same on both API levels.
