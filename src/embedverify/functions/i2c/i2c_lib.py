"""I2C function helper library."""

from __future__ import annotations

from typing import Any


def list_buses(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    cap = _i2c_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.list_buses(
        expected_count=int(params.get("expected_count", 1)),
        timeout=int(params.get("timeout", 10)),
    )


def scan(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    cap = _i2c_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    expected_addresses = params.get("expected_addresses", [])
    if not isinstance(expected_addresses, list):
        expected_addresses = [expected_addresses]
    return cap.scan(
        bus=str(params.get("bus", "auto")),
        expected_addresses=expected_addresses,
        min_device_count=int(params.get("min_device_count", 0)),
        timeout=int(params.get("timeout", 10)),
    )


def _i2c_cap(capability_registry: dict[str, Any] | None) -> Any:
    cap = (capability_registry or {}).get("i2c")
    if cap is None:
        return {"code": -2, "message": "i2c capability is not available", "details": {}, "metrics": {}}
    return cap
