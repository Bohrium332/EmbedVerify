"""I2C bus list function."""

from __future__ import annotations

from typing import Any

from .i2c_lib import list_buses


def execute(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """List I2C buses with a stable Function return contract."""

    return list_buses(params, capability_registry=capability_registry)
