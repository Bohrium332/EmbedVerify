"""Wi-Fi function helper library."""

from __future__ import annotations

from typing import Any


def detect(params: dict[str, Any], *, capability_registry: dict[str, Any] | None) -> dict[str, Any]:
    cap = _wifi_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.detect(
        interface=str(params.get("interface", "auto")),
        expected_count=int(params.get("expected_count", 1)),
        timeout=int(params.get("timeout", 10)),
    )


def scan(params: dict[str, Any], *, capability_registry: dict[str, Any] | None) -> dict[str, Any]:
    cap = _wifi_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.scan(
        interface=str(params.get("interface", "auto")),
        bring_up=_as_bool(params.get("bring_up", True)),
        min_network_count=int(params.get("min_network_count", 1)),
        timeout=int(params.get("timeout", 20)),
    )


def _wifi_cap(capability_registry: dict[str, Any] | None) -> Any:
    cap = (capability_registry or {}).get("wifi")
    if cap is None:
        return {"code": -2, "message": "wifi capability is not available", "details": {}, "metrics": {}}
    return cap


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes", "on")
