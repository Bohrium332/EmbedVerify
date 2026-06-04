"""SPI transfer function."""

from __future__ import annotations

from typing import Any

from .spi_lib import transfer


def execute(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a SPI transfer with a stable Function return contract."""

    return transfer(params, capability_registry=capability_registry)
