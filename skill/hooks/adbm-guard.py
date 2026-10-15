#!/usr/bin/env python3
"""PreToolUse hook for Read: keeps full-size adbm frames and raw UI dumps out of the context.

Denies a Read of a frame `build/adbm/<run>/api<N>/**.png` and of a raw `uiautomator` XML dump
`logs/ui-api<N>-*.xml`. The contact sheet, diff crops, diffs and `look/` images pass: they are
downscaled. A diff made with `adbm diff --full` has the same name as a 540 px one and passes too.
"""
import json
import re
import sys

FRAME = re.compile(r"/build/adbm/[^/]+/api\d+/.+\.png$")
XML = re.compile(r"/logs/ui-api\d+-[^/]*\.xml$")


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    path = str((data.get("tool_input") or {}).get("file_path") or "")
    if FRAME.search(path):
        why = ("adbm: full-size frame (~3350 tokens). Read the contact sheet, diff/*.crop.png or the "
               "540 px diff, or make a small copy: adbm thumb <frame> [--crop x0,y0,x1,y1].")
    elif XML.search(path):
        why = "adbm: raw UI dump. Use adbm ui --find <text> or grep the file for what you need."
    else:
        return 0
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": why}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
