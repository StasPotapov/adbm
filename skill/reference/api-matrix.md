# Which API levels to offer

The project's set lives in `[devices] apis` of `.adbm/config.ini` (`adbm config`). When it is empty,
a command without `--api` takes the one running emulator or API 35. The agent offers levels with a reason,
the person decides, and the agent writes the answer with `adbm config --set devices.apis=… --project`.
Never offer levels below the app's `minSdk`. Every extra level adds frames and time, but a parallel run on three emulators takes almost as long as on one.

| What the change touches | API levels | Why |
|---|---|---|
| Insets, navbar, status bar, BottomSheet, IME | 28, 33, 35 | 35 enforces edge-to-edge for targetSdk 35. 29+ has gesture navigation. 28 keeps the old inset behaviour |
| Gesture navigation, system back | 33, 35 (+ `nav=threebutton,gestural`) | no gestures before API 29. Predictive back appeared in 33 as an app opt-in. In 35 the system back animations work without developer options |
| Dark theme | 33, 35 (+ `theme=light,dark`) | on API 28 `cmd uimode night yes` did not darken the system Settings: 0.2% diff in the smoke test of 15.10.2026 |
| Permissions: notifications, photos, location | 32, 33, 34 | `POST_NOTIFICATIONS` since 33. Partial photo access since 34 |
| Fonts, scale, long strings | 35 (+ `font=1.0,1.3`) | barely depends on the API level, only the scale matters |
| Plain layout without system parts | 35 | one level is enough |
| Background work, foreground services | 33, 34, 35 | FGS types are required since 34. Background start limits grow with every release |
| Per-app locale | 33, 35 (+ `locale=…` and the app package) | `cmd locale set-app-locales` exists since 33 |

How to offer, example:
"The change touches the sheet insets. I suggest 28, 33, 35: edge-to-edge is enforced on 35,
28 has the old insets. Matrix: `nav=threebutton,gestural`; 28 has no gestures. OK?"

## Matrix axes of `adbm run --matrix`

| Axis | Values | What `adbm prep` does |
|---|---|---|
| `theme` | `light`, `dark` | `cmd uimode night no|yes` |
| `nav` | `threebutton`, `gestural` | `cmd overlay enable-exclusive …navbar.<x>`; below API 29 the `gestural` cell is skipped |
| `font` | a number, e.g. `1.0,1.3` | `settings put system font_scale` |
| `locale` | `ru-RU,en-US` | `cmd locale set-app-locales <package>`, API 33+ only |

Every cell is its own group subfolder. Subfolders follow the axis order in `--matrix`:
`--matrix "nav=…" "theme=…"` gives `api35/after/gestural/dark/1-peek.png`.
Before running a cell, `adbm run` deletes its old frames so attempts do not mix.
