"""Spawn a native VM and exchange RemGlk JSON events with it."""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
from pathlib import Path
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUILD_DIR = REPO_ROOT / "build"

VM_TABLE = [
    # (vm-id,         filename regex,             notes)
    ("bocfel",       re.compile(r"\.z[3458]$|\.zblorb$",     re.I)),
    ("glulxe",       re.compile(r"\.(gblorb|ulx)$",          re.I)),
    ("hugo",         re.compile(r"\.hex$",                   re.I)),
    ("scare",        re.compile(r"\.taf$",                   re.I)),
    ("tads",         re.compile(r"\.(gam|t3)$",              re.I)),
]


def detect_vm(storyfile: str | os.PathLike) -> str:
    name = os.fspath(storyfile)
    for vm, pat in VM_TABLE:
        if pat.search(name):
            return vm
    raise ValueError(f"Could not detect VM from filename: {name!r}")


def find_binary(vm: str, build_dir: Path | None = None) -> Path:
    build_dir = build_dir or DEFAULT_BUILD_DIR
    candidate = build_dir / vm
    if not candidate.exists():
        raise FileNotFoundError(
            f"VM binary not found: {candidate}\n"
            f"Build it with `./build.sh` from {REPO_ROOT}"
        )
    return candidate


class VMRunner:
    """Run a VM as a subprocess speaking line-delimited RemGlk JSON."""

    def __init__(
        self,
        storyfile: str | os.PathLike,
        vm: str | None = None,
        build_dir: Path | None = None,
        extra_args: list[str] | None = None,
    ):
        self.storyfile = os.fspath(storyfile)
        self.vm = vm or detect_vm(self.storyfile)
        self.binary = find_binary(self.vm, build_dir)
        self.extra_args = list(extra_args or [])
        self.proc: subprocess.Popen | None = None
        self.stderr_text: str = ""

    def __enter__(self) -> "VMRunner":
        self.proc = subprocess.Popen(
            [str(self.binary), *self.extra_args, self.storyfile],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def send(self, event: dict) -> None:
        assert self.proc and self.proc.stdin
        self.proc.stdin.write(json.dumps(event) + "\n")
        self.proc.stdin.flush()

    def recv(self) -> dict | None:
        """Read one update line. Returns None at EOF."""
        assert self.proc and self.proc.stdout
        while True:
            line = self.proc.stdout.readline()
            if not line:
                return None
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue

    def updates(self) -> Iterator[dict]:
        while True:
            u = self.recv()
            if u is None:
                return
            yield u

    def close(self) -> None:
        if not self.proc:
            return
        try:
            if self.proc.stdin:
                try:
                    self.proc.stdin.close()
                except OSError:
                    pass
            try:
                self.proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.proc.send_signal(signal.SIGTERM)
                try:
                    self.proc.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
            if self.proc.stderr:
                try:
                    self.stderr_text = self.proc.stderr.read() or ""
                except Exception:
                    pass
        finally:
            self.proc = None
