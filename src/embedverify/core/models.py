"""Domain models for suites, cases, functions, and reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class BoardProfile:
    """Board resource and capability declaration."""

    name: str
    platform: str
    adapter: str = "linux_generic"
    capabilities: dict[str, str] = field(default_factory=dict)
    interfaces: dict[str, Any] = field(default_factory=dict)
    tools_required: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FunctionSpec:
    """Function invocation loaded from a case."""

    name: str
    params: dict[str, Any] = field(default_factory=dict)
    expect: dict[str, Any] | None = None
    timeout: int | None = None
    enabled: bool = True


@dataclass(slots=True)
class CaseSpec:
    """Case workflow loaded from a case config."""

    name: str
    functions: list[FunctionSpec]
    description: str = ""
    module: str = ""
    execution: str = "sequential"


@dataclass(slots=True)
class SuiteSpec:
    """Suite scenario loaded from a suite config."""

    name: str
    cases: list[str]
    board: str | None = None
    description: str = ""
    execution: str = "sequential"
    report_enabled: bool = True


@dataclass(slots=True)
class ExecutionRecord:
    """Single function execution record."""

    case_name: str
    function_name: str
    result: dict[str, Any]
    expectation: dict[str, Any]
    started_at: str
    finished_at: str
    duration_ms: int


def utc_now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""

    return datetime.now(timezone.utc).isoformat()

