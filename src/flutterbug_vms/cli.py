"""Command-line entry point: pick a VM by file extension and run it.

By default, presents a cheap terminal interface (like emglken without --rem).
Pass --rem to passthrough RemGlk JSON over stdio (machine-readable).
"""
from __future__ import annotations

import argparse
import shutil
import sys

from .console import run_console
from .runner import VMRunner, detect_vm


VMS = ["bocfel", "bocfel-noz6", "git", "glulxe", "hugo", "scare", "tads"]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="flutterbug-vm",
        description="Run an interactive fiction VM against a story file.")
    p.add_argument("storyfile", help="path to the story file")
    p.add_argument("--vm", choices=VMS,
        help="force a specific VM (default: auto-detect by extension)")
    p.add_argument("--rem", action="store_true",
        help="passthrough RemGlk JSON on stdio instead of cheap console")
    args = p.parse_args(argv)

    vm = args.vm or detect_vm(args.storyfile)

    with VMRunner(args.storyfile, vm=vm) as runner:
        if args.rem:
            return _passthrough(runner)
        run_console(runner)
    return 0


def _passthrough(runner: VMRunner) -> int:
    """Pump stdin → VM stdin and VM stdout → stdout. RemGlk JSON, machine-readable."""
    import select, os
    proc = runner.proc
    assert proc and proc.stdin and proc.stdout
    in_fd = sys.stdin.fileno()
    out_fd = proc.stdout.fileno()
    while True:
        rlist, _, _ = select.select([in_fd, out_fd], [], [])
        if out_fd in rlist:
            line = proc.stdout.readline()
            if not line:
                break
            sys.stdout.write(line)
            sys.stdout.flush()
        if in_fd in rlist:
            data = os.read(in_fd, 4096)
            if not data:
                try: proc.stdin.close()
                except OSError: pass
                # drain
                for line in proc.stdout:
                    sys.stdout.write(line)
                break
            proc.stdin.write(data.decode("utf-8", errors="replace"))
            proc.stdin.flush()
    return proc.wait()
