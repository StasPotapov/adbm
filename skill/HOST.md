# Host capability contract

Keep the entire `skill/` directory together. Resolve `bin/adbm`, `reference/` and
`agents/` relative to the loaded `SKILL.md`, including when it is reached by symlink.
In a Claude Code plugin, use `${CLAUDE_SKILL_DIR}` if the client supplied it, otherwise
use the displayed skill base directory. Codex uses the path shown for the discovered skill.
Do not assume that `adbm` is on PATH.

Run the CLI from the Android project, not from the installed skill directory. Outputs, caches,
credentials and user data belong outside the package. Set `PYTHONDONTWRITEBYTECODE=1`
if the package should be kept free of Python bytecode.

Use the current host's file, shell, image, question and background-session APIs.
Names such as Read, Bash, Glob, Task or Artifact in older examples describe a
capability, not a required tool name. Inspect the actual tool schema before calling.
Without a background API, run synchronously with a suitable timeout. Without an
image viewer, do not claim a visual check. Without a connector, use the documented
local-file route or report the missing dependency. Do not invent tool calls.
For Wi-Fi pairing, the QR must be visible while `pair` is running. If you cannot
stream its output, use `pair --open` on a visible local desktop or let the person run
it in their terminal; the QR is deleted when pairing exits.

The CLI needs a local shell with access to the Android SDK and a connected device or
emulator. Other clients can follow this skill even if they have no native skill loader.
Use [visual-check.md](reference/visual-check.md#the-adbm-eyes-subagent) for the Codex,
Claude Code and other client routes to a visual verdict. Never translate model names by guesswork.
If independent agents or required isolation are unavailable, report that limitation;
a local deterministic result is not an independent visual verdict. Hook files also
need native installation and trust; their presence alone does not enforce a guard.

Dependencies are not bundled executables. Check the tool's documented prerequisites;
installing this skill does not authorize logging in, changing devices or services,
installing system software, publishing, or switching an existing executor.
