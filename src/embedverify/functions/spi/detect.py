"""SPI detection function."""

from __future__ import annotations

from typing import Any

from .spi_lib import detect


def execute(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Detect SPI spidev devices with a stable Function return contract."""

    return detect(params, capability_registry=capability_registry)
