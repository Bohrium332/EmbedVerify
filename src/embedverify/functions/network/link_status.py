"""Network link status function."""

from __future__ import annotations

from typing import Any

from .network_lib import link_status


def execute(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check network link status with a stable Function return contract."""

    return link_status(params, capability_registry=capability_registry)
