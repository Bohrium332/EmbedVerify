"""GPIO chip list function."""

from __future__ import annotations

from typing import Any

from .gpio_lib import list_chips


def execute(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """List GPIO chips with a stable Function return contract."""

    return list_chips(params, capability_registry=capability_registry)
