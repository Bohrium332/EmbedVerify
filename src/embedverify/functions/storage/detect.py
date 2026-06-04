"""Storage detection function."""

from __future__ import annotations

from typing import Any

from .storage_lib import detect_storage


def execute(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Detect storage devices with a stable Function return contract."""

    return detect_storage(params, capability_registry=capability_registry)
