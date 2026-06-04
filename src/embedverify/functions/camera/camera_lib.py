"""Camera function helper library."""

from __future__ import annotations

from typing import Any


def detect(params: dict[str, Any], *, capability_registry: dict[str, Any] | None) -> dict[str, Any]:
    cap = _camera_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.detect(
        sensor_id=int(params.get("sensor_id", 0)),
        probe_capture=_as_bool(params.get("probe_capture", True)),
        timeout=int(params.get("timeout", 12)),
    )


def capture_smoke(params: dict[str, Any], *, capability_registry: dict[str, Any] | None) -> dict[str, Any]:
    cap = _camera_cap(capability_registry)
    if isinstance(cap, dict):
        return cap
    return cap.capture_smoke(
        sensor_id=int(params.get("sensor_id", 0)),
        width=int(params.get("width", 1280)),
        height=int(params.get("height", 720)),
        framerate=int(params.get("framerate", 30)),
        timeout=int(params.get("timeout", 12)),
    )


def _camera_cap(capability_registry: dict[str, Any] | None) -> Any:
    cap = (capability_registry or {}).get("camera")
    if cap is None:
        return {"code": -2, "message": "camera capability is not available", "details": {}, "metrics": {}}
    return cap


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes", "on")
