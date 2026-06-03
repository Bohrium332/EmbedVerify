"""Storage write speed function."""

from __future__ import annotations

from typing import Any

from .storage_lib import write_speed


def execute(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Measure storage write speed with a stable Function return contract."""

    return write_speed(params, capability_registry=capability_registry)

