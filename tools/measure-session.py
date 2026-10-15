#!/usr/bin/env python3
"""What an agent session spent on adbm: output per command, images, Read calls.

Usage: measure-session.py <transcript.jsonl> [more.jsonl …]
A transcript is a Claude Code session file: ~/.claude/projects/<project>/<session>.jsonl,
a subagent transcript is in <session>/subagents/. Tokens are estimates: text ~4 characters
per token, an image by its pixels (w × h / 784), from the PNG or JPEG header.
"""
import base64
import collections
import json
import os
import re
import struct
import sys

CLI = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "skill", "bin", "adbm")
COMMANDS = set(re.findall(r'^\s*(?:p = )?add\("([a-z][a-z-]*)"', open(CLI).read(), re.M))
# `adbm ui`, `"$ADBM" ui`, `.../bin/adbm ui`
ADBM = re.compile(r"adbm\}?\"?\s+([a-z][a-z-]*)", re.I)


def image_size(data):
    """(w, h) of a PNG or JPEG."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    i = 2
    while data[:2] == b"\xff\xd8" and i + 9 < len(data):
        if data[i] != 0xFF:
            break
        marker, size = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        i += 2 + size
    return 0, 0


def image_tokens(data_b64):
    try:
        w, h = image_size(base64.b64decode(data_b64))
    except Exception:
        return 0
    return -(-w // 28) * -(-h // 28)


def text_of(content):
    if isinstance(content, str):
        return content, []
    texts, images = [], []
    for b in content or []:
        if b.get("type") == "text":
            texts.append(b["text"])
        elif b.get("type") == "image":
            images.append(image_tokens(b.get("source", {}).get("data", "")))
    return "\n".join(texts), images


def measure(paths):
    uses = {}
    rows = collections.defaultdict(lambda: {"calls": 0, "chars": 0, "images": 0, "image_tokens": 0})
    seen = set()
    for p in paths:
        for line in open(p):
            try:
                e = json.loads(line)
            except ValueError:
                continue
            content = (e.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for b in content:
                if b.get("type") == "tool_use":
                    inp = b.get("input") or {}
                    if b["name"] == "Bash":
                        cmds = [c for c in ADBM.findall(inp.get("command", "")) if c in COMMANDS]
                        key = f"adbm {cmds[0]}" if cmds else "Bash (other)"
                    elif b["name"] == "Read":
                        f = inp.get("file_path", "")
                        key = "Read image" if re.search(r"\.(png|jpe?g|webp)$", f, re.I) else "Read text"
                    else:
                        key = b["name"]
                    uses[b["id"]] = key
                elif b.get("type") == "tool_result" and b.get("tool_use_id") not in seen:
                    seen.add(b.get("tool_use_id"))
                    key = uses.get(b.get("tool_use_id"), "?")
                    text, images = text_of(b.get("content"))
                    r = rows[key]
                    r["calls"] += 1
                    r["chars"] += len(text)
                    r["images"] += len(images)
                    r["image_tokens"] += sum(images)
    return rows


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        return 2
    rows = measure(sys.argv[1:])
    print(f"{'what':<22} {'calls':>5} {'chars':>8} {'~tok':>7} {'images':>6} {'~img tok':>8}")
    tot = collections.Counter()
    for k, r in sorted(rows.items(), key=lambda kv: -(kv[1]["chars"] // 4 + kv[1]["image_tokens"])):
        print(f"{k:<22} {r['calls']:>5} {r['chars']:>8} {r['chars'] // 4:>7} {r['images']:>6} {r['image_tokens']:>8}")
        tot.update(r)
    print(f"{'total':<22} {tot['calls']:>5} {tot['chars']:>8} {tot['chars'] // 4:>7} {tot['images']:>6} {tot['image_tokens']:>8}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
