#!/usr/bin/env python3
"""Drive each native VM with a short RemGlk JSON conversation."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flutterbug_vms.runner import VMRunner

REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = REPO_ROOT / "emglken" / "tests"

CASES = [
    ("glulxe",      "advent.ulx",   ["east", "look"]),
    ("git",         "advent.ulx",   ["east", "look"]),
    ("bocfel",      "advent.z5",    ["east", "look"]),
    ("bocfel-noz6", "advent.z5",    ["east", "look"]),
    ("hugo",        "colossal.hex", ["east", "look"]),
    ("scare",       "Hamper.taf",   ["look", "wait"]),
    ("tads",        "ditch.gam",    ["look", "wait"]),
]


def extract_text(update: dict) -> list[str]:
    out = []
    for w in update.get("content") or []:
        for chunk in (w.get("text") or w.get("lines") or []):
            for c in chunk.get("content") or []:
                t = c.get("text", "")
                if t.strip():
                    out.append(t)
    return out


def run_case(vm: str, story: str, commands: list[str]) -> tuple[bool, list[str], str]:
    storyfile = TESTS_DIR / story
    text_seen: list[str] = []
    err = ""
    runner = VMRunner(storyfile, vm=vm)
    runner.__enter__()
    try:
        runner.send({"type": "init", "gen": 0,
                     "metrics": {"width": 80, "height": 50},
                     "support": ["timer"]})
        u = runner.recv()
        if u: text_seen.extend(extract_text(u))

        for i, cmd in enumerate(commands, start=1):
            try:
                runner.send({"type": "line", "gen": i,
                             "window": 1, "value": cmd})
            except (BrokenPipeError, OSError):
                break
            u = runner.recv()
            if u: text_seen.extend(extract_text(u))

        # Try to terminate cleanly.
        gen = len(commands)
        for closer in ["quit", "yes", "y"]:
            gen += 1
            try:
                runner.send({"type": "line", "gen": gen,
                             "window": 1, "value": closer})
            except (BrokenPipeError, OSError):
                break
            runner.recv()
    finally:
        runner.close()
        err = runner.stderr_text
    return bool(text_seen), text_seen, err.strip()


def main() -> int:
    results = []
    for vm, story, cmds in CASES:
        print(f"\n=== {vm} ({story}) ===")
        try:
            ok, text, err = run_case(vm, story, cmds)
        except Exception as e:
            ok, text, err = False, [], repr(e)
        print(f"  text-chunks: {len(text)}  ok: {ok}")
        for line in text[:5]:
            print(f"  | {line[:90]}")
        if err:
            print(f"  STDERR: {err[:300]}")
        results.append((vm, ok))

    print("\n=== summary ===")
    for vm, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {vm}")
    return 0 if all(ok for _, ok in results) else 1


if __name__ == "__main__":
    sys.exit(main())
