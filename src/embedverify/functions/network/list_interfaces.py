"""Network interface list function."""

from __future__ import annotations

from typing import Any

from .network_lib import list_interfaces


def execute(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """List network interfaces with a stable Function return contract."""

    return list_interfaces(params, capability_registry=capability_registry)
