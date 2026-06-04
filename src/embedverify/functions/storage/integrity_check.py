"""Storage data integrity check function."""

from __future__ import annotations

from typing import Any

from .storage_lib import integrity_check


def execute(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify storage write/read integrity with a stable Function return contract."""

    return integrity_check(params, capability_registry=capability_registry)
