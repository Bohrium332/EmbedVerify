"""Bluetooth scan function."""

from __future__ import annotations

from typing import Any

from .bluetooth_lib import scan


def execute(params: dict[str, Any], *, capability_registry: dict[str, Any] | None = None) -> dict[str, Any]:
    """Scan Bluetooth devices with a stable Function return contract."""

    return scan(params, capability_registry=capability_registry)
