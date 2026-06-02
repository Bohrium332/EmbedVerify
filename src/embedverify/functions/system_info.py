"""Stable system information functions."""

from __future__ import annotations

from typing import Any


def collect(*, capability_registry: dict[str, Any] | None = None) -> dict[str, Any]:
    """Collect platform-normalized system information."""

    cap = (capability_registry or {}).get("system_info")
    if cap is None:
        return {
            "code": -2,
            "status": "failed",
            "message": "system_info capability is not available",
            "details": {},
            "metrics": {},
        }
    return cap.collect()

