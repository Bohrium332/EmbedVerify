"""Storage information function."""

from __future__ import annotations

from typing import Any

from .storage_lib import storage_info


def execute(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return storage information with a stable Function return contract."""

    return storage_info(params, capability_registry=capability_registry)

