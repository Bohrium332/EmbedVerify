"""USB device detection function."""

from __future__ import annotations

from typing import Any

from .usb_lib import detect_devices


def execute(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Detect USB devices with a stable Function return contract."""

    return detect_devices(params, capability_registry=capability_registry)

