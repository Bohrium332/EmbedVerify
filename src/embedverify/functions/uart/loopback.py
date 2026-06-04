"""UART loopback function."""

from __future__ import annotations

from typing import Any

from .uart_lib import loopback


def execute(params: dict[str, Any], *, capability_registry: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run UART loopback with a stable Function return contract."""

    return loopback(params, capability_registry=capability_registry)
