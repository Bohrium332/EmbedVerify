"""Capability base helpers."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class CommandResult:
    """Normalized command result."""

    returncode: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    """Protocol for command execution."""

    def __call__(self, args: list[str], timeout: int) -> CommandResult:
        """Run a command."""


def run_command(args: list[str], timeout: int) -> CommandResult:
    """Run a command and normalize the result."""

    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return CommandResult(result.returncode, result.stdout, result.stderr)

