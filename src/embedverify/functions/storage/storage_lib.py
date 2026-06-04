"""Storage function helper library."""

from __future__ import annotations

from typing import Any


def detect_storage(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    cap = _storage_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.detect(
        device=str(params.get("device", "")),
        expected_type=str(params.get("expected_type", "")),
        min_size_bytes=int(params.get("min_size_bytes", 0)),
        transport=str(params.get("transport", "")),
        timeout=int(params.get("timeout", 10)),
    )


def storage_info(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    cap = _storage_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.info(
        device=str(params.get("device", "")),
        mount_point=str(params.get("mount_point", "")),
        timeout=int(params.get("timeout", 10)),
    )


def read_speed(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    cap = _storage_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.read_speed(
        device=str(params.get("device", "auto")),
        method=str(params.get("method", "auto")),
        min_speed_mbps=float(params.get("min_speed_mbps", 0)),
        timeout=int(params.get("timeout", 120)),
    )


def write_speed(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    cap = _storage_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.write_speed(
        device=str(params.get("device", "")),
        mount_point=str(params.get("mount_point", "auto")),
        file_size_mb=int(params.get("file_size_mb", 256)),
        min_speed_mbps=float(params.get("min_speed_mbps", 0)),
        timeout=int(params.get("timeout", 120)),
    )


def integrity_check(
    params: dict[str, Any],
    *,
    capability_registry: dict[str, Any] | None,
) -> dict[str, Any]:
    cap = _storage_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.integrity_check(
        device=str(params.get("device", "")),
        mount_point=str(params.get("mount_point", "auto")),
        file_size_mb=int(params.get("file_size_mb", 64)),
        timeout=int(params.get("timeout", 300)),
    )


def _storage_cap(capability_registry: dict[str, Any] | None) -> Any:
    cap = (capability_registry or {}).get("storage")
    if cap is None:
        return {
            "code": -2,
            "message": "storage capability is not available",
            "details": {},
            "metrics": {},
        }
    return cap
