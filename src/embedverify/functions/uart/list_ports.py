"""UART port list function."""

from __future__ import annotations

from typing import Any

from .uart_lib import list_ports


def execute(params: dict[str, Any], *, capability_registry: dict[str, Any] | None = None) -> dict[str, Any]:
    """List UART/serial ports with a stable Function return contract."""

    return list_ports(params, capability_registry=capability_registry)
