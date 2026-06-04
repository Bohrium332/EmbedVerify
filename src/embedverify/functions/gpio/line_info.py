"""GPIO line information function."""

from __future__ import annotations

from typing import Any

from .gpio_lib import line_info


def execute(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read GPIO line information with a stable Function return contract."""

    return line_info(params, capability_registry=capability_registry)
