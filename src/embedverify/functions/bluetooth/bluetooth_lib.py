"""Bluetooth function helper library."""

from __future__ import annotations

from typing import Any


def detect(params: dict[str, Any], *, capability_registry: dict[str, Any] | None) -> dict[str, Any]:
    cap = _bluetooth_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.detect(
        require_powered=_as_bool(params.get("require_powered", True)),
        timeout=int(params.get("timeout", 10)),
    )


def scan(params: dict[str, Any], *, capability_registry: dict[str, Any] | None) -> dict[str, Any]:
    cap = _bluetooth_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.scan(
        timeout=int(params.get("timeout", 8)),
        min_device_count=int(params.get("min_device_count", 1)),
    )


def _bluetooth_cap(capability_registry: dict[str, Any] | None) -> Any:
    cap = (capability_registry or {}).get("bluetooth")
    if cap is None:
        return {"code": -2, "message": "bluetooth capability is not available", "details": {}, "metrics": {}}
    return cap


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes", "on")
