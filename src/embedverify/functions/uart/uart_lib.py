"""UART function helper library."""

from __future__ import annotations

from typing import Any


def list_ports(params: dict[str, Any], *, capability_registry: dict[str, Any] | None) -> dict[str, Any]:
    cap = _uart_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.list_ports(expected_count=int(params.get("expected_count", 1)))


def loopback(params: dict[str, Any], *, capability_registry: dict[str, Any] | None) -> dict[str, Any]:
    cap = _uart_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.loopback(
        port=str(params.get("port", "auto")),
        payload=str(params.get("payload", "EV_UART_LOOPBACK")),
        baudrate=int(params.get("baudrate", 115200)),
        timeout=float(params.get("timeout", 2.0)),
    )


def _uart_cap(capability_registry: dict[str, Any] | None) -> Any:
    cap = (capability_registry or {}).get("uart")
    if cap is None:
        return {"code": -2, "message": "uart capability is not available", "details": {}, "metrics": {}}
    return cap
