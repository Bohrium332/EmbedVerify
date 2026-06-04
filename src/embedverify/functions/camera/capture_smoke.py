"""Camera capture smoke function."""

from __future__ import annotations

from typing import Any

from .camera_lib import capture_smoke


def execute(params: dict[str, Any], *, capability_registry: dict[str, Any] | None = None) -> dict[str, Any]:
    """Capture one CSI frame into a fakesink with a stable Function return contract."""

    return capture_smoke(params, capability_registry=capability_registry)
