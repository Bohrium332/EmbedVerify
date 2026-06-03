"""Stable storage test functions."""

from __future__ import annotations

from typing import Any


def info(
    *,
    device: str = "",
    mount_point: str = "",
    timeout: int = 10,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return storage information with a stable output contract."""

    cap = _storage_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.info(device=device, mount_point=mount_point, timeout=timeout)


def read_speed(
    *,
    device: str = "auto",
    method: str = "auto",
    min_speed_mbps: float = 0,
    timeout: int = 120,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Measure block-device read speed with a stable output contract."""

    cap = _storage_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.read_speed(
        device=device,
        method=method,
        min_speed_mbps=min_speed_mbps,
        timeout=timeout,
    )


def write_speed(
    *,
    mount_point: str = "auto",
    file_size_mb: int = 256,
    min_speed_mbps: float = 0,
    timeout: int = 120,
    capability_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Measure mounted-filesystem write speed with a stable output contract."""

    cap = _storage_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.write_speed(
        mount_point=mount_point,
        file_size_mb=file_size_mb,
        min_speed_mbps=min_speed_mbps,
        timeout=timeout,
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
