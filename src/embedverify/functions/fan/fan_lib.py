"""Fan function helper library."""

from __future__ import annotations

from typing import Any


def info(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    cap = _fan_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.info(
        expected_count=int(params.get("expected_count", 1)),
        min_rpm=int(params.get("min_rpm", 0)),
    )


def _fan_cap(capability_registry: dict[str, Any] | None) -> Any:
    cap = (capability_registry or {}).get("fan")
    if cap is None:
        return {"code": -2, "message": "fan capability is not available", "details": {}, "metrics": {}}
    return cap
