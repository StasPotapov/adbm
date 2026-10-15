# Environment and builds

## Requirements

| What | Why | How to install |
|---|---|---|
| Android SDK: `platform-tools`, `emulator`, `cmdline-tools` | adb, emulators, `sdkmanager` and `avdmanager` | Android Studio → SDK Manager → SDK Tools |
| Java 17+ | Maestro, `sdkmanager`, Gradle | macOS: `brew install openjdk@17`; Linux: `sudo apt install openjdk-17-jdk` |
| Python 3.9+ and Pillow | `adbm` itself: contact sheet, diff, `look` | `python3 -m pip install Pillow`; Homebrew Python: `brew install pillow`; Debian/Ubuntu: `sudo apt install python3-pil` |
| Maestro | `adbm run`, `adbm type` with non-ASCII text | `adbm setup --maestro --yes` (Homebrew `mobile-dev-inc/tap/maestro`, without Homebrew the official `get.maestro.mobile.dev` script) |
| ffmpeg | contact sheet in `adbm record` | macOS: `brew install ffmpeg`; Linux: `sudo apt install ffmpeg` |
| Android CLI, optional | `adbm annotate` and `tap '#N'` on screens without a UI tree; the rest works without it | `adbm setup --android-cli --yes` (Homebrew cask `android-cli`; without Homebrew install it by hand) |
| SDK licenses | `sdkmanager` downloads images only after they are accepted | the person runs `sdkmanager --licenses` and accepts them; `adbm setup` stops and says so |
| Guard hook (Claude Code) | denies `Read` of full-size frames | `adbm setup --hook --yes`: appends to `~/.claude/settings.json`; a plugin install has it |
| `adbm-eyes` agent (Claude Code) | the subagent with 5 tools, a small start context | `adbm setup --agent --yes`: a link in `~/.claude/agents/`; a plugin install has it |

`adbm doctor` checks all of this and prints a fix command for every row.
Settings: `adbm config` shows the model and effort of `adbm-eyes` and the project's API levels.
`--set devices.apis=28,33,35 --project` writes `.adbm/config.ini`, without `--project` — `~/.config/adbm/config.ini`;
the project file wins. `--init` writes a file with all keys and comments; in the project file the keys
are commented out, so it overrides nothing until you set a value.
`doctor` itself installs nothing.

Platforms: macOS is tested. Linux: the emulator needs `/dev/kvm`; `devices --start --headless` uses the
software GPU there. Windows is not supported.

## `adbm setup`

Without `--yes` the command only prints the plan. Show the plan to the person and wait for consent.

```bash
adbm setup                           # plan for the API levels of the config: missing images, AVDs, tuning
adbm setup --api 28,33,35 --yes      # other levels, run it
adbm setup --tune --yes              # raise memory, disk and cores in config.ini of existing AVDs
adbm setup --maestro --android-cli --yes
```

- **What is skipped:** an API level that already has a phone AVD (Wear, TV, Automotive and tablet AVDs
  do not count). An image already on disk is reused: the variant from `[devices] image`, or, when none
  is set, any phone variant (`google_apis`, `google_apis_playstore`, `default`, `google_atd`, `aosp_atd`).
- **System image** — `system-images;android-N;<image>;<abi>`, downloaded by `sdkmanager` from Google's repository
  into `$ANDROID_HOME/system-images/`: `arm64-v8a` on Apple Silicon, `x86_64` otherwise.
  `image` is `google_apis` by default: it allows `adb root`, a `google_apis_playstore` image does not.
- **AVD** is created as `adbm_API_N` on the `[devices] profile` profile, `pixel_8` by default.
- **Tuning** of `config.ini` raises `hw.ramSize` to 4096, `vm.heapSize` to 576, `hw.cores` to 4 and
  `disk.dataPartition.size` to 8G; bigger values stay. `hw.keyboard=yes` and `hw.gpu.mode=host` are set exactly.
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
