# Similar tools

[Русский](alternatives.ru.md) · [README](../README.md)

These tools cover part of what ADBM does. The comparison is as of October 2026, based on the projects'
READMEs and documentation.

## The agent drives a device

These tools give an agent taps, typing, the UI tree, screenshots and logs. Here ADBM duplicates what exists.

- [mobile-mcp](https://github.com/mobile-next/mobile-mcp) — an MCP server for Android and iOS, ~9.5k stars.
  It works through the accessibility tree first and falls back to screenshots only when needed.
  Its README mentions no parallel work on several devices and no frame comparison.
- [Maestro MCP](https://docs.maestro.dev/get-started/maestro-mcp) ships inside the Maestro CLI: devices, screen,
  flow runs, screenshots. It works with Claude Code, Codex, Cursor and other agents.
- Google's [Android CLI](https://developer.android.com/tools/agents/android-cli), version 1.0 since May 2026.
  The binary is closed source and telemetry is on by default. ADBM uses it only for `annotate`.
- Smaller skills and MCP servers: [android-adb-skill](https://github.com/amit-nayar/android-adb-skill),
  [claude-adb-skill](https://github.com/pengdev/claude-adb-skill),
  [android-testing-skills](https://github.com/skydoves/android-testing-skills),
  [DroidMind](https://archestra.ai/mcp-catalog/hyperb1iss__droidmind),
  [android-mcp](https://github.com/remymazmanian/android-mcp).

ADBM adds only details here: `tap` prints what changed on the screen, and `ui` compresses the tree.

## Tests in natural language

A person describes a scenario in words, and a model decides where to tap.

- [Journeys](https://developer.android.com/tools/agents/android-cli/journeys) in Android CLI.
- The [App Testing agent](https://firebase.google.com/docs/app-distribution/android/app-testing-agent) in Firebase, on Gemini.
- [android-qa-agent](https://github.com/tobrun/android-qa-agent) records Claude's actions and replays them,
  on one device only.

The model walks such a scenario anew on every run, so the steps can differ. In ADBM a Maestro flow
sets the scenario: it is the same in every matrix cell, so frames can be compared pixel by pixel.

## Visual regression

- [Maestro `assertScreenshot`](https://docs.maestro.dev/reference/commands-available/assertscreenshot)
  (CLI 2.2.0, March 2026) compares the screen with a reference image by a threshold, 95% by default.
  This is the closest tool. Reference images must be captured and stored.
- [Emerge / Sentry Snapshots](https://docs.emergetools.com/docs/android-snapshots-v1) compare the snapshots
  of a PR build with those of the base build. Snapshots come from `@Preview`, not from the running app. The service is cloud-based.
- Roborazzi, Paparazzi, Shot need test code and golden images in git.
- Percy and Applitools are cloud-based and paid.

## How ADBM differs

Other tools give the agent taps, screenshots or a comparison with reference images. ADBM runs the whole check
of a change and gives you a ready result. You fix a bug or add a component. The agent runs the scenario
on the "before" and "after" builds and compares the frames. Then you open one page and see whether the change works
the way you meant.

- **The agent spends few tokens.** Full-size frames never enter the agent's context: a hook blocks reading them.
  The agent navigates by the text of the UI tree. Python computes what changed, pixel by pixel, without a model.
  A subagent on a cheap model looks at the frames and returns text to the agent. The run's `stats.json` shows the cost.
- **The agent does everything itself.** It boots the emulators, installs both builds and runs one Maestro flow
  on all API levels in parallel. The scenario runs in every cell of the API × theme × navigation × font scale matrix.
  `prep` turns off animations and turns on demo mode, so frames differ only because of your change.
- **No reference images.** ADBM compares two builds on one scenario. You do not prepare reference images,
  test code or `@Preview`.
- **The result is on one page.** The board shows the changed frames and a verdict for each: EXPECTED, PROBLEM or REVIEW.
  The subagent writes the verdict against your task checklist. You can view a pair side by side, with a slider, as a diff,
  as the changed area only or as the status bar. When the same change is on another API level, the board marks it `≈ API N`.

Other tools have each part separately. We found no tool with the whole combination.

## Where ADBM is weaker

- Android only. mobile-mcp and Maestro work with iOS too.
- The subagent and the hook work only in Claude Code. Maestro MCP and Android CLI fit any agent.
- No CI mode and no device cloud, only local emulators.
- Tested on macOS and on a small number of apps.
