"""RK-specific capability placeholders for future boards."""

from __future__ import annotations

from typing import Any


class RKSystemInfoCapability:
    """Placeholder for future RK-specific system info collection."""

    def collect(self) -> dict[str, Any]:
        """Return a stable Function contract for system info."""

        return {
            "code": 0,
            "message": "RK system info capability is available",
            "details": {"adapter": "rk"},
            "metrics": {},
        }
