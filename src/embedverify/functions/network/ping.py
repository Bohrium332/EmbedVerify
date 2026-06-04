"""Network ping function."""

from __future__ import annotations

from typing import Any

from .network_lib import ping


def execute(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ping a host with a stable Function return contract."""

    return ping(params, capability_registry=capability_registry)
