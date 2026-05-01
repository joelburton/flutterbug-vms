"""Cheap terminal renderer for RemGlk JSON updates.

Mirrors the spirit of asyncglk's CheapGlkOte: print plain text from buffer
windows, render the status line from the topmost grid window, and read line
input from stdin.
"""
from __future__ import annotations

import shutil
import sys
from typing import TextIO

from .runner import VMRunner


def _terminal_size() -> tuple[int, int]:
    size = shutil.get_terminal_size(fallback=(80, 50))
    return size.columns, max(size.lines, 5)


def _render_grid(window: dict) -> list[str]:
    out = []
    for line in window.get("lines", []):
        text = "".join(c.get("text", "") for c in line.get("content", []))
        out.append(text)
    return out


def _render_buffer(window: dict) -> list[str]:
    out = []
    for para in window.get("text", []):
        if para.get("append"):
            chunks = [c.get("text", "") for c in para.get("content", [])]
            if out:
                out[-1] += "".join(chunks)
            else:
                out.append("".join(chunks))
        else:
            chunks = [c.get("text", "") for c in para.get("content", [])]
            out.append("".join(chunks))
    return out


def run_console(
    runner: VMRunner,
    *,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
) -> None:
    """Drive a VMRunner in cheap-console mode until the VM exits."""
    width, height = _terminal_size()
    gen = 0
    runner.send({
        "type": "init",
        "gen": gen,
        "metrics": {"width": width, "height": height},
        "support": ["timer"],
    })

    pending_input: dict | None = None
    last_grid_lines: list[str] = []

    def flush_buffers(update: dict) -> None:
        nonlocal last_grid_lines
        windows = update.get("content") or []
        for w in windows:
            wid = w.get("id")
            if "lines" in w:  # grid window (status line)
                last_grid_lines = _render_grid(w)
            elif "text" in w:  # buffer window
                lines = _render_buffer(w)
                for line in lines:
                    stdout.write(line + "\n")
        stdout.flush()

    while True:
        update = runner.recv()
        if update is None:
            return
        if update.get("type") != "update":
            continue

        flush_buffers(update)

        # If we have a status line, redraw it briefly above the prompt.
        if last_grid_lines:
            for line in last_grid_lines:
                stdout.write(f"\x1b[7m{line[:width]:<{width}}\x1b[0m\n")
            stdout.flush()

        # Look for an input request to know what to ask for next.
        inputs = update.get("input") or []
        if not inputs:
            continue

        req = inputs[0]
        gen = req.get("gen", gen + 1)
        kind = req.get("type")
        try:
            if kind == "line":
                stdout.write("> ")
                stdout.flush()
                line = stdin.readline()
                if not line:
                    return
                runner.send({"type": "line", "gen": gen,
                             "window": req["id"], "value": line.rstrip("\n")})
            elif kind == "char":
                stdout.write("[press a key, then Enter] ")
                stdout.flush()
                line = stdin.readline()
                if not line:
                    return
                ch = line[:1] if line and line[0] != "\n" else "return"
                runner.send({"type": "char", "gen": gen,
                             "window": req["id"], "value": ch})
            else:
                # Unknown input kind — bail.
                return
        except (BrokenPipeError, OSError):
            return
