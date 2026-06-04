"""Network function helper library."""

from __future__ import annotations

from typing import Any


def list_interfaces(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    cap = _network_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.list_interfaces(
        include_loopback=_as_bool(params.get("include_loopback", False)),
        expected_count=int(params.get("expected_count", 1)),
        timeout=int(params.get("timeout", 10)),
    )


def link_status(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    cap = _network_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.link_status(
        interface=str(params.get("interface", "auto")),
        require_up=_as_bool(params.get("require_up", True)),
        require_carrier=_as_bool(params.get("require_carrier", False)),
        timeout=int(params.get("timeout", 10)),
    )


def ping(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    cap = _network_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.ping(
        host=str(params.get("host", "gateway")),
        count=int(params.get("count", 3)),
        timeout=int(params.get("timeout", 10)),
        interface=str(params.get("interface", "")),
    )


def _network_cap(capability_registry: dict[str, Any] | None) -> Any:
    cap = (capability_registry or {}).get("network")
    if cap is None:
        return {"code": -2, "message": "network capability is not available", "details": {}, "metrics": {}}
    return cap


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes", "on")
