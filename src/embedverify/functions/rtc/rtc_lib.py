"""RTC function helper library."""

from __future__ import annotations

from typing import Any


def list_devices(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    cap = _rtc_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.list_devices(expected_count=int(params.get("expected_count", 1)))


def read(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    cap = _rtc_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.read(
        device=str(params.get("device", "auto")),
        timeout=int(params.get("timeout", 10)),
    )


def _rtc_cap(capability_registry: dict[str, Any] | None) -> Any:
    cap = (capability_registry or {}).get("rtc")
    if cap is None:
        return {"code": -2, "message": "rtc capability is not available", "details": {}, "metrics": {}}
    return cap
