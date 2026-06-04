"""Wi-Fi scan function."""

from __future__ import annotations

from typing import Any

from .wifi_lib import scan


def execute(params: dict[str, Any], *, capability_registry: dict[str, Any] | None = None) -> dict[str, Any]:
    """Scan Wi-Fi networks with a stable Function return contract."""

    return scan(params, capability_registry=capability_registry)
