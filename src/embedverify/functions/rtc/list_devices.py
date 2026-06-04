"""RTC device list function."""

from __future__ import annotations

from typing import Any

from .rtc_lib import list_devices


def execute(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """List RTC devices with a stable Function return contract."""

    return list_devices(params, capability_registry=capability_registry)
