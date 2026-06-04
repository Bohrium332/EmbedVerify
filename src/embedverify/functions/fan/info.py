"""Fan information function."""

from __future__ import annotations

from typing import Any

from .fan_lib import info


def execute(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read fan telemetry with a stable Function return contract."""

    return info(params, capability_registry=capability_registry)
