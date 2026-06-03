"""Jetson-specific capability placeholders."""

from __future__ import annotations

from typing import Any


class JetsonSystemInfoCapability:
    """Collect a small, stable system info subset from Jetson boards."""

    def collect(self) -> dict[str, Any]:
        """Return a stable Function contract for system info."""

        return {
            "code": 0,
            "message": "Jetson system info capability is available",
            "details": {"adapter": "jetson"},
            "metrics": {},
        }
