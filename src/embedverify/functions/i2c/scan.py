"""I2C scan function."""

from __future__ import annotations

from typing import Any

from .i2c_lib import scan


def execute(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Scan an I2C bus with a stable Function return contract."""

    return scan(params, capability_registry=capability_registry)
