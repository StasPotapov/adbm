# Environment and builds

## Requirements

| What | Why | How to install |
|---|---|---|
| Android SDK: `platform-tools`, `emulator`, `cmdline-tools` | adb, emulators, `sdkmanager` and `avdmanager` | Android Studio → SDK Manager → SDK Tools |
| Java 17+ | Maestro, `sdkmanager`, Gradle | `brew install openjdk@17` |
| Python 3.9+ and Pillow | `adbm` itself: contact sheet, diff, `look` | `python3 -m pip install Pillow` |
| Maestro | `adbm run`, `adbm type` with non-ASCII text | `adbm setup --maestro --yes` (Homebrew `mobile-dev-inc/tap/maestro`) |
| ffmpeg | contact sheet in `adbm record` | `brew install ffmpeg` |
| Android CLI, optional | only `adbm annotate` | `adbm setup --android-cli --yes` (cask `android-cli`) |
| Guard hook (Claude Code) | denies `Read` of full-size frames | `adbm setup --hook --yes`: appends to `~/.claude/settings.json`; a plugin install has it |
| `adbm-eyes` agent (Claude Code) | the subagent with 5 tools, a small start context | `adbm setup --agent --yes`: a link in `~/.claude/agents/`; a plugin install has it |

`adbm doctor` checks all of this and prints a fix command for every row.
`doctor` itself installs nothing.

## `adbm setup`

Without `--yes` the command only prints the plan. Show the plan to the person and wait for consent.

```bash
adbm setup --api 28,33,35            # plan: system images, AVDs, tuning
adbm setup --api 28,33,35 --yes      # run it
adbm setup --tune --yes              # fix config.ini of existing AVDs
adbm setup --maestro --android-cli --yes
```

- **System image** — `system-images;android-N;google_apis;<abi>`: `arm64-v8a` on Apple Silicon, `x86_64` otherwise.
  A `google_apis` image allows `adb root`, a `playstore` image does not.
- **AVD** is created as `adbm_API_N` on the `pixel_8` profile.
- **Tuning** of `config.ini`: `hw.ramSize=4096`, `vm.heapSize=576`, `hw.cores=4`,
  `disk.dataPartition.size=8G`, `hw.keyboard=yes`, `hw.gpu.mode=host`.
  With 2 GB of RAM an API 35 emulator is slow, and Maestro hits timeouts.
  `hw.keyboard=yes` keeps the on-screen keyboard out of frames.
- **A running AVD** is skipped by `--tune`: the config is read only at boot.

## Android CLI

A closed-source Google binary with a JVM inside. Telemetry is on by default.
`adbm` passes `--no-metrics` to every call. Do not run `android init`: it installs its own
skill into every agent folder.

`adbm annotate` calls `android screen capture --annotate --device <serial> -o <png>`.
The boxes come from computer vision on the image, not from the UI tree. Then `adbm tap '#N'`
calls `android screen resolve --screenshot <png> --string '#N'` and gets `x y`.
Use it for screens with an empty tree: Canvas, games, WebView without accessibility.

## Emulators

```bash
adbm devices                      # API → serial → AVD → screen
adbm devices --start 28,33,35     # boot missing ones, wait for sys.boot_completed
adbm devices --start 35 --headless
```

The emulator boot log is `~/.cache/adbm/emu-<AVD>.log`.

## "Before" and "after" builds

First check the app's `minSdk` (`grep -rn minSdk` over `build.gradle*` and `libs.versions.toml`).
`adbm install` also prints `minSdk` and `targetSdk` from the APK and skips devices below `minSdk`.

"After" is the current code: `./gradlew :app:assembleDebug`.

Build "before" from the base commit in a separate worktree so the working copy stays untouched:

```bash
BASE=$(git merge-base HEAD origin/main)       # or the commit before the change
git worktree add ../<repo>-before $BASE
(cd ../<repo>-before && ./gradlew :app:assembleDebug)
adbm install ../<repo>-before/app/build/outputs/apk/debug/app-debug.apk --as before --api 28,33,35
adbm install app/build/outputs/apk/debug/app-debug.apk --as after --api 28,33,35
git worktree remove ../<repo>-before          # after the check
```

If the change is not made yet, it is simpler to capture "before" on the current code right away,
and "after" once the change is done. For a throwaway experiment you can also edit the file,
build "after", copy the APK and revert the file with `git checkout -- <file>`.

Both APKs share one `applicationId`, so a device holds one version at a time.
The order is: install "before", capture all "before", install "after", capture all "after".
`adbm install` writes the package, `minSdk`, `targetSdk` and sha1 to the run's `builds.json`; the board shows them.
